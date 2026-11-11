#!/usr/bin/env python3
"""Collect the deterministic fact packet for the daily-review skill; output is analysis data."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402
import skill_verification  # noqa: E402

SCHEMA = "daily-review.collect.v1"
CLI = "daily-review-collect"
COMMANDS = ["collect", "usage"]
TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
THREAD_FIELDS = ["id", "title", "cwd", "source", "thread_source", "archived",
                 "rollout_path", "created_at_ms", "updated_at_ms"]
# Codex edits files through tools.apply_patch inside exec; the patch is a JS string, so stop at quotes/escapes.
SKILL_EDIT = re.compile(r"\*\*\* (?:Add|Update) File: ([^\s\"'\\]+/SKILL\.md)")
BEGIN = re.compile(r"skill[-_]verification(?:\.py)?\S*\s+(?:--root\s+\S+\s+)?begin\b")
AUTOMATION_ID = re.compile(r"Automation ID: ([A-Za-z0-9_-]+)")
TOML_STRING = re.compile(r'^(model|reasoning_effort)\s*=\s*"([^"]*)"', re.MULTILINE)
CLAUDE_EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}


def window(day: date) -> dict[str, Any]:
    start = datetime.combine(day, datetime.min.time(), TZ)
    end = start + timedelta(days=1)
    return {"date": day.isoformat(), "timezone": "Asia/Shanghai",
            "start_ms": int(start.timestamp() * 1000), "end_ms": int(end.timestamp() * 1000)}


def threads(db: Path, span: dict[str, Any], gaps: list[str]) -> list[dict[str, Any]]:
    """Recall rule from the daily-review skill: created before window end, updated within or after it."""
    query = (f"SELECT {', '.join(THREAD_FIELDS)} FROM threads "
             "WHERE created_at_ms < ? AND updated_at_ms >= ? ORDER BY created_at_ms")
    for mode in ("ro", "ro&immutable=1"):
        try:
            connection = sqlite3.connect(f"file:{db}?mode={mode}", uri=True)
            try:
                rows = connection.execute(query, (span["end_ms"], span["start_ms"])).fetchall()
            finally:
                connection.close()
            if mode != "ro":
                gaps.append("threads_db_read_as_immutable_snapshot")
            return [{"client": "codex", **dict(zip(THREAD_FIELDS, row))} for row in rows]
        except sqlite3.Error:
            continue
    gaps.append(f"threads_db_unreadable:{db}")
    return []


def rollout_file(path: str | None, codex_home: Path) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_file():
        return candidate
    archived = codex_home / "archived_sessions" / candidate.name
    return archived if archived.is_file() else None


def stamp_ms(stamp: str | None) -> int | None:
    try:
        return int(datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def in_window(stamp: str | None, span: dict[str, Any]) -> bool:
    moment = stamp_ms(stamp)
    return moment is not None and span["start_ms"] <= moment < span["end_ms"]


def add_segment(models: list[dict[str, Any]], model: Any, effort: Any, stamp: str | None) -> None:
    """Model and effort can change between turns of one session, so keep one segment per change."""
    if not models or (models[-1]["model"], models[-1]["effort"]) != (model, effort):
        models.append({"model": model, "effort": effort, "from": stamp})


def obligation(edited: set[str], begins: list[str]) -> dict[str, Any] | None:
    # begin may name the skill through the repo path, a ~/.ai symlink or a relative path; match the skill directory name.
    missing = sorted(path for path in edited
                     if not any(f"/{Path(path).parent.name}" in text or f" {Path(path).parent.name}" in text
                                for text in begins))
    return {"edited_skills": sorted(edited), "missing_begin": missing} if edited else None


def has_begin_call(text: str) -> bool:
    """Recognize a direct call or a literal executable alias in the same command.

    Do not evaluate shell input or carry variables across separate tool processes.
    """
    if BEGIN.search(text):
        return True
    for match in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)=['\"]?([^\s;'\"\\]*skill[-_]verification(?:\.py)?)(?=['\"\s;\\]|$)['\"]?", text):
        call = re.search(r"\$(?:" + re.escape(match[1]) + r"\b|\{" + re.escape(match[1]) + r"\})"
                         r"\s+(?:--root\s+\S+\s+)?begin\b", text[match.end():])
        if call:
            return True
    return False


def scan_rollout(rollout: Path, span: dict[str, Any]) -> dict[str, Any]:
    """One pass over a rollout: model segments and SKILL.md edits inside the window, begin calls and automation id."""
    edited: set[str] = set()
    begins: list[str] = []
    models: list[dict[str, Any]] = []
    automation_id = None
    with rollout.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            payload = item.get("payload") or {}
            # Only the automation's own prompt names it; tool output may quote other automations.
            if (automation_id is None and "Automation ID:" in line and payload.get("type") == "message"
                    and payload.get("role") == "user"):
                found = AUTOMATION_ID.search(line)
                automation_id = found.group(1) if found else None
            if item.get("type") == "turn_context":
                if in_window(item.get("timestamp"), span):
                    add_segment(models, payload.get("model"), payload.get("effort"), item.get("timestamp"))
                continue
            if item.get("type") != "response_item" or payload.get("type") not in {"custom_tool_call", "function_call"}:
                continue
            text = str(payload.get("input") or payload.get("arguments") or "")
            if has_begin_call(text):
                begins.append(text)
            if in_window(item.get("timestamp"), span):
                edited.update(SKILL_EDIT.findall(text))
    return {"models": models, "automation_id": automation_id, "obligation": obligation(edited, begins)}


def scan_claude(path: Path, span: dict[str, Any]) -> dict[str, Any] | None:
    """One pass over a Claude Code session: the same facts as a Codex thread, from its own record shapes."""
    first = last = session_id = cwd = title = None
    entrypoints: set[str] = set()
    models: list[dict[str, Any]] = []
    edited: set[str] = set()
    begins: list[str] = []
    human_turns = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            moment = stamp_ms(item.get("timestamp")) if item.get("timestamp") else None
            if moment is not None:
                first, last = first if first is not None else moment, moment
            session_id, cwd = session_id or item.get("sessionId"), cwd or item.get("cwd")
            if item.get("entrypoint"):
                entrypoints.add(item["entrypoint"])
            kind, inside = item.get("type"), in_window(item.get("timestamp"), span)
            if kind == "ai-title":
                title = item.get("aiTitle")
            elif kind == "user" and inside and item.get("turnOrigin") == "human":
                human_turns += 1
            if kind != "assistant":
                continue
            message = item.get("message") or {}
            # Synthetic records such as API error notices carry "<synthetic>" instead of a model.
            if inside and not str(message.get("model")).startswith("<"):
                add_segment(models, message.get("model"), item.get("effort"), item.get("timestamp"))
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                data = block.get("input") or {}
                if block.get("name") == "Bash" and has_begin_call(str(data.get("command", ""))):
                    begins.append(str(data["command"]))
                elif (inside and block.get("name") in CLAUDE_EDIT_TOOLS
                      and str(data.get("file_path", "")).endswith("/SKILL.md")):
                    edited.add(str(data["file_path"]))
    if first is None:
        return None
    return {"client": "claude", "id": session_id or path.stem, "title": title, "cwd": cwd,
            "entrypoints": sorted(entrypoints), "rollout_path": str(path), "rollout_found": True,
            "created_at_ms": first, "updated_at_ms": last, "human_turns": human_turns, "models": models,
            "obligation": obligation(edited, begins)}


def claude_sessions(projects: Path, span: dict[str, Any], gaps: list[str]) -> list[dict[str, Any]]:
    """Main sessions at <projects>/<project>/<session>.jsonl, recalled by the same rule as Codex threads."""
    if not projects.is_dir():
        gaps.append(f"claude_projects_missing:{projects}")
        return []
    found = []
    for path in sorted(projects.glob("*/*.jsonl")):
        try:
            # mtime is never earlier than the last record, so it is a safe prefilter for "updated within or after".
            if path.stat().st_mtime * 1000 < span["start_ms"]:
                continue
            session = scan_claude(path, span)
        except OSError as exc:
            gaps.append(f"claude_session_unreadable:{path}:{exc}")
            continue
        if session and session["created_at_ms"] < span["end_ms"] and session["updated_at_ms"] >= span["start_ms"]:
            found.append(session)
    return found


def automation_config(codex_home: Path, automation_id: str) -> dict[str, Any] | None:
    """Configured model and effort of an automation; the actual per-turn values are in the thread's models."""
    config = codex_home / "automations" / automation_id / "automation.toml"
    if not config.is_file():
        return None
    values = dict(TOML_STRING.findall(config.read_text(encoding="utf-8", errors="replace")))
    return {"model": values.get("model"), "effort": values.get("reasoning_effort")}


def unsettled_receipts(audits: Path) -> list[str]:
    return sorted(str(receipt) for receipt in audits.glob("*/receipt.json")
                  if not (receipt.parent / "settlement.json").exists())


def ledger(root: Path) -> dict[str, Any]:
    summary = skill_verification.status(argparse.Namespace(
        root=root, change_id=None, open_only=True, limit=10_000))
    changes = summary["changes"]
    return {
        "open_count": len(changes),
        "open": [{"change_id": item["change_id"], "skill_id": item["skill_id"],
                  "verdict": item["evaluation"]["verdict"], "summary": item["summary"],
                  "updated_at": item["updated_at"]} for item in changes],
    }


def collect(args: argparse.Namespace) -> dict[str, Any]:
    span = window(args.date)
    gaps: list[str] = []
    recalled = threads(args.db, span, gaps)
    obligations = []
    for thread in recalled:
        rollout = rollout_file(thread["rollout_path"], args.codex_home)
        thread["rollout_found"] = rollout is not None
        if rollout is None:
            gaps.append(f"rollout_missing:{thread['id']}")
            continue
        scanned = scan_rollout(rollout, span)
        thread["models"] = scanned["models"]
        if scanned["automation_id"]:
            thread["automation"] = {"id": scanned["automation_id"],
                                    "configured": automation_config(args.codex_home, scanned["automation_id"])}
        found = scanned["obligation"]
        if found and found["missing_begin"]:
            obligations.append({"thread_id": thread["id"], "obligation": "skill_verification_begin", **found})
    for session in claude_sessions(args.claude_projects, span, gaps):
        found = session.pop("obligation")
        if found and found["missing_begin"]:
            obligations.append({"thread_id": session["id"], "obligation": "skill_verification_begin", **found})
        recalled.append(session)
    recalled.sort(key=lambda thread: thread["created_at_ms"])
    try:
        verification = ledger(args.ledger_root)
    except (OSError, ValueError, KeyError) as exc:
        verification = None
        gaps.append(f"ledger_unreadable:{exc}")
    return {
        "schema": SCHEMA,
        "contract": "analysis data for skills/daily-review; facts only, no dispositions",
        "window": span,
        "threads": recalled,
        "audit_receipts_unsettled": unsettled_receipts(args.audits),
        "skill_verification": verification,
        "obligations": obligations,
        "limitations": ["SKILL.md edits are detected from Codex apply_patch and Claude Code Edit/Write/MultiEdit calls; "
                        "edits made by shell commands are not detected",
                        "begin matching checks the edited skill directory name appears in a begin call of the same thread",
                        "models lists model or effort changes inside the window; a turn continued from before the window has no entry",
                        "Claude Code recall covers main sessions under <projects>/<project>/<session>.jsonl; "
                        "subagent transcripts are not recalled"],
        "gaps": gaps,
    }


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("collect", help="emit the fact packet for one Asia/Shanghai calendar day")
    run.add_argument("--date", type=parse_date,
                     default=(datetime.now(TZ) - timedelta(days=1)).date(),
                     help="YYYY-MM-DD; defaults to yesterday")
    run.add_argument("--db", type=Path, default=home / ".codex/state_5.sqlite")
    run.add_argument("--codex-home", type=Path, default=home / ".codex")
    run.add_argument("--claude-projects", type=Path, default=home / ".claude/projects")
    run.add_argument("--ledger-root", type=Path, default=skill_verification.default_root())
    run.add_argument("--audits", type=Path, default=home / ".ai/audits/save-context")
    run.set_defaults(handler=collect)
    usage = commands.add_parser("usage", help="local call statistics")
    usage.set_defaults(handler=lambda _args: cli_usage.summarize(CLI, COMMANDS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started, code = time.monotonic(), 0
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        code = 2
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
