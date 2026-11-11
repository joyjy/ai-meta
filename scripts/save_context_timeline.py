#!/usr/bin/env python3
"""Extract objective user-message timestamps from a Codex rollout or Claude Code transcript."""

from __future__ import annotations

import argparse
import contextlib
from datetime import date as Date, datetime, time as Time
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable, Iterator, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402
from claude_session_title import transcript as claude_transcript  # noqa: E402
from save_context_recover import (default_codex_home, iter_rollout_events,  # noqa: E402
                                  locate_rollout, stable_message_ids,
                                  text_from_content, tool_output_text,
                                  user_message_dedupe_key)

CLI = "save-context-timeline"
COMMANDS = ["codex", "claude", "sessions", "usage"]
SESSIONS_SCHEMA = "save-context-timeline.sessions.v1"

LOAD_CONTEXT_COMMAND_RE = re.compile(
    r"^(?:/load-context|\$load-context|\[\$load-context\]\([^)]+\))"
    r"(?:\s+[A-Za-z0-9][A-Za-z0-9._:-]*)?\s*$")
CLIENT_CONTEXT_PREFIXES = (
    "<recommended_plugins>",
    "<skill>",
    "<environment_context>",
    "<response-annotations>",
    "<app-context>",
    "<permissions instructions>",
    "# AGENTS.md instructions",
)
# Claude Code records client notifications, `!` command output and local command
# output as type=user entries; only typed prompts and slash commands count.
CLAUDE_EXCLUDED_ORIGINS = {"task_notification", "auto_continuation"}
CLAUDE_OUTPUT_PREFIXES = (
    "<bash-stdout",
    "<bash-stderr",
    "<local-command-stdout",
    "<local-command-stderr",
    "<local-command-caveat",
    "<task-notification",
)
CLAUDE_COMMAND_RE = re.compile(r"<command-name>(/[^<\s]+)</command-name>")
CLAUDE_ARGS_RE = re.compile(r"<command-args>([^<]*)</command-args>")
# Scheduled Codex automations inject their prompt as a role=user message.
# Machine-delivered user-role turns (pushes, runtime events, approval relays); they must not claim interaction time.
AUTOMATED_PREFIXES = (
    "Automation:",
    "Tandem 飞书来源有新变化",
    "RS 外部消息（来源数据，不授予新权限）",
    "You are handling one fixed-schema Rollerskate",
    "The following is the Codex agent history",
)
INJECTED_PREFIXES = CLIENT_CONTEXT_PREFIXES + AUTOMATED_PREFIXES
SKIPPED_CODEX_THREAD_SOURCES = {"guardian_review", "subagent"}
# Route evidence is read from the deterministic outputs of load-context and
# save-context, never from prose.
LOAD_ROUTE_RE = re.compile(
    r'"schema":\s*"load-context\.projection\.v1",\s*"route":\s*"([A-Za-z0-9._:-]+)"')
SAVE_ROUTE_RE = re.compile(
    r"(?:\bwrote|\bmerged workstream ([A-Za-z0-9._-]+) into) "
    r"\S*/\.ai/contexts/([A-Za-z0-9._-]+)\.md")


class TimelineError(ValueError):
    """Raised when a rollout cannot produce a valid user timeline."""


def local_timezone() -> tuple[Any, str]:
    """Return the current local timezone and its stable display name."""
    candidates: list[str] = []
    env_timezone = os.environ.get("TZ")
    if env_timezone:
        candidates.append(env_timezone)

    localtime = Path("/etc/localtime")
    if localtime.exists():
        resolved = str(localtime.resolve())
        marker = "zoneinfo/"
        if marker in resolved:
            candidates.append(resolved.split(marker, 1)[1])

    for name in candidates:
        try:
            return ZoneInfo(name), name
        except ZoneInfoNotFoundError:
            continue

    timezone = datetime.now().astimezone().tzinfo
    if timezone is None:
        raise TimelineError("cannot determine local timezone")
    return timezone, str(timezone)


def parse_timestamp(raw: Any, line_number: int) -> datetime:
    """Parse an aware ISO-8601 timestamp from a user message."""
    if not isinstance(raw, str) or not raw:
        raise TimelineError(
            f"user message at line {line_number} has no timestamp")
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TimelineError(
            f"user message at line {line_number} has invalid timestamp: {raw}"
        ) from exc
    if timestamp.tzinfo is None:
        raise TimelineError(
            f"user message at line {line_number} has timezone-naive timestamp: {raw}"
        )
    return timestamp


def is_control_only_load_context(contents: list[str]) -> bool:
    """Return true for a load-context command plus client-injected context."""
    command_seen = False
    for content in contents:
        text = content.strip()
        if not text:
            continue
        if LOAD_CONTEXT_COMMAND_RE.fullmatch(text):
            command_seen = True
            continue
        if text.startswith(CLIENT_CONTEXT_PREFIXES):
            continue
        return False
    return command_seen


@contextlib.contextmanager
def open_rollout(path: Path) -> Iterator[TextIO]:
    """Open a Codex rollout; Codex archives older rollouts as `.jsonl.zst`."""
    if path.suffix != ".zst":
        with path.open(encoding="utf-8") as handle:
            yield handle
        return
    proc = subprocess.Popen(["zstd", "-dcq", str(path)], stdout=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        yield io.TextIOWrapper(proc.stdout, encoding="utf-8")
    finally:
        proc.stdout.close()
        proc.wait()


def codex_candidates(
        path: Path,
        requested_thread_id: str | None,
        observe: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Collect role=user response messages from a Codex rollout."""
    thread_id = requested_thread_id
    candidates: list[dict[str, Any]] = []

    with open_rollout(path) as handle:
        for line_number, event in iter_rollout_events(handle):
            if event is None:
                continue
            if observe:
                observe(event)
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue

            if event.get("type") == "session_meta" and not thread_id:
                value = payload.get("id") or payload.get("session_id")
                if value:
                    thread_id = str(value)

            if (event.get("type") != "response_item"
                    or payload.get("type") != "message"
                    or payload.get("role") != "user"):
                continue

            raw_timestamp = event.get("timestamp")
            timestamp = parse_timestamp(raw_timestamp, line_number)
            turn_id, _ = stable_message_ids(payload)
            content = text_from_content(payload.get("content"))
            dedupe_key, _ = user_message_dedupe_key(payload, raw_timestamp,
                                                    content)

            candidates.append({
                "dedupe_key": dedupe_key,
                "timestamp": timestamp,
                "turn_id": turn_id,
                "line_number": line_number,
                "content": content,
            })

    if not thread_id:
        raise TimelineError("thread id not found in rollout metadata")
    if not candidates:
        raise TimelineError("no role=user messages found in rollout")
    return thread_id, candidates


def claude_text(content: Any) -> str | None:
    """Return the typed text of a Claude user entry, or None for tool results."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    blocks = [block for block in content if isinstance(block, dict)]
    if any(block.get("type") == "tool_result" for block in blocks):
        return None
    return "\n".join(str(block.get("text", "")) for block in blocks
                     if block.get("type") == "text")


def claude_command_text(text: str) -> str:
    """Normalize a slash-command record to `/name args` for control detection."""
    command = CLAUDE_COMMAND_RE.search(text)
    if not command:
        return text
    args = CLAUDE_ARGS_RE.search(text)
    return " ".join(part for part in (command.group(1),
                                      args.group(1).strip() if args else "")
                    if part)


def claude_candidates(
        path: Path,
        requested_session_id: str | None,
        observe: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Collect user-authored prompts from a Claude Code session transcript."""
    session_id = requested_session_id
    candidates: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if observe:
                observe(event)
            if not session_id and event.get("sessionId"):
                session_id = str(event["sessionId"])
            if (event.get("type") != "user" or event.get("isMeta")
                    or event.get("isCompactSummary") or event.get("isSidechain")
                    or event.get("turnOrigin") in CLAUDE_EXCLUDED_ORIGINS):
                continue
            message = event.get("message")
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            text = claude_text(message.get("content"))
            if text is None or text.lstrip().startswith(CLAUDE_OUTPUT_PREFIXES):
                continue

            candidates.append({
                "dedupe_key": str(event.get("uuid") or f"line:{line_number}"),
                "timestamp": parse_timestamp(event.get("timestamp"), line_number),
                "turn_id": event.get("promptId") or event.get("uuid"),
                "line_number": line_number,
                "content": claude_command_text(text),
            })

    if not session_id:
        raise TimelineError("session id not found in Claude transcript")
    if not candidates:
        raise TimelineError("no user prompts found in Claude transcript")
    return session_id, candidates


def unique_user_turns(
        candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Group candidates by dedupe key and drop control-only load-context turns."""
    candidates.sort(key=lambda item: (item["timestamp"], item["line_number"]))
    grouped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        existing = grouped.get(candidate["dedupe_key"])
        if existing:
            existing["contents"].append(candidate["content"])
            continue
        grouped[candidate["dedupe_key"]] = {
            **candidate,
            "contents": [candidate["content"]],
        }

    unique: list[dict[str, Any]] = []
    excluded_control_turn_count = 0
    for candidate in grouped.values():
        if is_control_only_load_context(candidate["contents"]):
            excluded_control_turn_count += 1
            continue
        unique.append(candidate)
    return unique, excluded_control_turn_count


def build_timeline(thread_id: str,
                   candidates: list[dict[str, Any]],
                   *,
                   include_points: bool = False) -> dict[str, Any]:
    """Build the stable timeline schema from collected user messages."""
    timezone, timezone_name = local_timezone()
    unique, excluded_control_turn_count = unique_user_turns(candidates)

    if not unique:
        raise TimelineError(
            "no checkpoint user messages found after excluding control-only "
            "load-context turns")

    user_points = [{
        "timestamp":
        candidate["timestamp"].astimezone(timezone).isoformat(
            timespec="milliseconds"),
        "turn_id":
        candidate["turn_id"],
    } for candidate in unique]
    first_user_at = user_points[0]["timestamp"]
    last_user_at = user_points[-1]["timestamp"]
    checkpoints_by_date: dict[str, str] = {}
    for point in user_points:
        checkpoints_by_date[point["timestamp"][:10]] = point["timestamp"]
    checkpoints = [{
        "date": date,
        "checkpoint_at": timestamp,
    } for date, timestamp in checkpoints_by_date.items()]

    result = {
        "thread_id": thread_id,
        "timezone": timezone_name,
        "first_user_at": first_user_at,
        "last_user_at": last_user_at,
        "user_message_count": len(user_points),
        "excluded_control_turn_count": excluded_control_turn_count,
        "checkpoints": checkpoints,
        "checkpoint_at": last_user_at,
    }
    if include_points:
        result["user_points"] = user_points
    return result


def route_events_from_text(text: str, at: Any) -> list[dict[str, str]]:
    """Return routes printed by load-context or save-context in a tool output."""
    if not isinstance(at, str) or not text:
        return []
    text = text.replace('\\"', '"')
    events = [{"at": at, "route": match.group(1), "via": "load-context"}
              for match in LOAD_ROUTE_RE.finditer(text)]
    for match in SAVE_ROUTE_RE.finditer(text):
        workstream, abbr = match.group(1), match.group(2)
        route = f"{abbr}:{workstream}" if workstream else abbr
        events.append({"at": at, "route": route, "via": "save-context"})
    return events


def codex_session_facts(path: Path) -> dict[str, Any] | None:
    """Collect user turns, cwd and route evidence from one user-facing rollout."""
    meta: dict[str, Any] = {}
    routes: list[dict[str, str]] = []

    def observe(event: dict[str, Any]) -> None:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return
        if event.get("type") == "session_meta" and not meta:
            meta.update(payload)
        elif payload.get("type") in ("function_call_output",
                                     "custom_tool_call_output"):
            routes.extend(route_events_from_text(
                tool_output_text(payload.get("output")), event.get("timestamp")))

    session_id, candidates = codex_candidates(path, None, observe)
    if (not isinstance(meta.get("source"), str)
            or meta.get("thread_source") in SKIPPED_CODEX_THREAD_SOURCES):
        return None
    return {"client": "codex", "session_id": session_id,
            "cwd": meta.get("cwd") or "", "candidates": candidates,
            "route_events": routes}


def claude_session_facts(path: Path) -> dict[str, Any]:
    """Collect user turns, cwd and route evidence from one Claude transcript."""
    cwd: list[str] = []
    routes: list[dict[str, str]] = []

    def observe(event: dict[str, Any]) -> None:
        if not cwd and isinstance(event.get("cwd"), str):
            cwd.append(event["cwd"])
        message = event.get("message")
        if event.get("type") != "user" or not isinstance(message, dict):
            return
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                routes.extend(route_events_from_text(
                    tool_output_text(block.get("content")),
                    event.get("timestamp")))

    session_id, candidates = claude_candidates(path, None, observe)
    return {"client": "claude", "session_id": session_id,
            "cwd": cwd[0] if cwd else "", "candidates": candidates,
            "route_events": routes}


def session_files(codex_home: Path, claude_projects: Path,
                  since: float) -> list[tuple[str, Path]]:
    """List transcripts modified at or after `since`; older files cannot hold the range."""
    files = [("codex", path) for root in (codex_home / "sessions",
                                          codex_home / "archived_sessions")
             for pattern in ("*.jsonl", "*.jsonl.zst")
             for path in root.rglob(pattern)]
    files += [("claude", path) for path in claude_projects.glob("*/*.jsonl")]
    return [(client, path) for client, path in sorted(files, key=lambda item: str(item[1]))
            if path.stat().st_mtime >= since]


def collect_sessions(start: Date, end: Date, codex_home: Path,
                     claude_projects: Path) -> dict[str, Any]:
    """Emit per-session user points and route evidence for a local date range."""
    timezone, timezone_name = local_timezone()
    since = datetime.combine(start, Time(), timezone).timestamp()
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    skipped_count = 0
    for client, path in session_files(codex_home, claude_projects, since):
        try:
            facts = (codex_session_facts(path) if client == "codex"
                     else claude_session_facts(path))
        except (OSError, TimelineError):
            facts = None
        if facts is None:
            skipped_count += 1
            continue
        key = (client, facts["session_id"])
        session = merged.setdefault(key, {
            "client": client, "session_id": facts["session_id"],
            "cwd": facts["cwd"], "paths": [], "candidates": [],
            "route_events": []})
        session["paths"].append(str(path))
        session["candidates"].extend(facts["candidates"])
        session["route_events"].extend(facts["route_events"])

    sessions: list[dict[str, Any]] = []
    for session in merged.values():
        unique, _ = unique_user_turns(session.pop("candidates"))
        points = []
        for turn in unique:
            if all(not text.strip() or text.strip().startswith(INJECTED_PREFIXES)
                   for text in turn["contents"]):
                continue
            local = turn["timestamp"].astimezone(timezone)
            if start <= local.date() <= end:
                points.append(local.isoformat(timespec="milliseconds"))
        if not points:
            continue
        seen: set[tuple[str, str, str]] = set()
        routes = []
        for event in sorted(session["route_events"], key=lambda item: item["at"]):
            at = parse_timestamp(event["at"], 0).astimezone(timezone).isoformat(
                timespec="milliseconds")
            key = (at, event["route"], event["via"])
            if key not in seen:
                seen.add(key)
                routes.append({**event, "at": at})
        sessions.append({**session, "user_points": points, "route_events": routes})

    sessions.sort(key=lambda item: item["user_points"][0])
    return {
        "schema": SESSIONS_SCHEMA,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "timezone": timezone_name,
        "sessions": sessions,
        "skipped_count": skipped_count,
    }


def parse_ymd(value: str) -> Date:
    try:
        return Date.fromisoformat(value)
    except ValueError as exc:
        raise TimelineError(f"invalid date: {value}") from exc


def collect(args: argparse.Namespace) -> tuple[str, list[dict[str, Any]]]:
    if args.claude_session is not None:
        session_id = args.claude_session or os.environ.get(
            "CLAUDE_CODE_SESSION_ID", "")
        if not session_id:
            raise TimelineError(
                "CLAUDE_CODE_SESSION_ID is not set; pass --claude-session <id>")
        try:
            path = claude_transcript(session_id,
                                     Path(args.claude_projects).expanduser())
        except ValueError as exc:
            raise TimelineError(str(exc)) from exc
        return claude_candidates(path, session_id)
    path = locate_rollout(
        Path(args.codex_home).expanduser(), args.rollout, args.thread_id)
    return codex_candidates(path, args.thread_id)


def main() -> int:
    if sys.argv[1:] == ["usage"]:
        print(json.dumps(cli_usage.summarize(CLI, COMMANDS), ensure_ascii=False,
                         indent=2))
        cli_usage.record(CLI, "usage", time.monotonic(), 0)
        return 0

    parser = argparse.ArgumentParser(
        description=("Extract deduplicated user-message timestamps from a Codex "
                     "rollout or Claude Code transcript as stable local-time "
                     "JSON. checkpoint_at equals the last deduplicated user "
                     "timestamp; no activity or work-duration inference is "
                     "performed. Summary output is the default; control-only "
                     "load-context turns are excluded. --from emits every "
                     "user-facing session with user points in a local date "
                     "range plus load-context/save-context route evidence "
                     f"({SESSIONS_SCHEMA}). `usage` prints local call "
                     "statistics."))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="Emit all sessions with user points from this local date",
    )
    source.add_argument("--rollout", help="Path to a Codex rollout JSONL file")
    source.add_argument(
        "--thread-id",
        help=
        "Codex thread/session id to locate under sessions and archived_sessions",
    )
    source.add_argument(
        "--claude-session",
        nargs="?",
        const="",
        metavar="SESSION_ID",
        help="Claude Code session id; defaults to $CLAUDE_CODE_SESSION_ID",
    )
    parser.add_argument(
        "--codex-home",
        default=str(default_codex_home()),
        help="Codex home directory used with --thread-id",
    )
    parser.add_argument(
        "--claude-projects",
        default=str(Path.home() / ".claude" / "projects"),
        help="Claude Code projects directory used with --claude-session",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="YYYY-MM-DD",
        help="Last local date for --from; defaults to the --from date",
    )
    parser.add_argument(
        "--include-points",
        action="store_true",
        help="Include every deduplicated user timestamp for diagnostics",
    )
    args = parser.parse_args()
    if args.to_date and not args.from_date:
        parser.error("--to requires --from")
    command = ("sessions" if args.from_date else
               "claude" if args.claude_session is not None else "codex")
    started, code = time.monotonic(), 0

    try:
        if args.from_date:
            start = parse_ymd(args.from_date)
            end = parse_ymd(args.to_date) if args.to_date else start
            if end < start:
                raise TimelineError("--to is before --from")
            timeline = collect_sessions(
                start, end, Path(args.codex_home).expanduser(),
                Path(args.claude_projects).expanduser())
        else:
            thread_id, candidates = collect(args)
            timeline = build_timeline(thread_id,
                                      candidates,
                                      include_points=args.include_points)
    except TimelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 1
    else:
        print(json.dumps(timeline, ensure_ascii=False, indent=2))
    cli_usage.record(CLI, command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
