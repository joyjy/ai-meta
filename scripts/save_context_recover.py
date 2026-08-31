#!/usr/bin/env python3
"""Build a compact recovery packet from a Codex rollout JSONL file.

This script is deliberately read-only. It helps a fresh thread recover evidence
from an old or archived Codex session without asking that old thread to run
another model turn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator

ABS_PATH_RE = re.compile(
    r"/Users/[^\s`\"')\]}>,]+|/private/tmp/[^\s`\"')\]}>,]+|/tmp/[^\s`\"')\]}>,]+"
)
CONTEXT_START_RE = re.compile(
    r"(?m)(?:^---[ \t]*\n#[ \t]*context:[ \t]*project=(?P<standard>[^;\n]+);[^\n]*$|"
    r"^<!--[ \t]*context:[ \t]*project=(?P<legacy>[^;\n]+);[^\n]*-->$)"
)


def default_codex_home() -> Path:
    return Path.home() / ".codex"


def locate_rollout(codex_home: Path, rollout: str | None,
                   thread_id: str | None) -> Path:
    if rollout:
        path = Path(rollout).expanduser()
        if not path.exists():
            raise SystemExit(f"rollout not found: {path}")
        return path

    if not thread_id:
        raise SystemExit("provide --rollout or --thread-id")

    roots = [codex_home / "sessions", codex_home / "archived_sessions"]
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        matches.extend(path for path in root.rglob("*.jsonl")
                       if thread_id in path.name)

    if not matches:
        raise SystemExit(f"rollout not found for thread id: {thread_id}")
    if len(matches) > 1:
        paths = "\n".join(str(path) for path in sorted(matches))
        raise SystemExit(
            f"multiple rollouts found for thread id {thread_id}:\n{paths}")
    return matches[0]


def iter_rollout_events(
        lines: Iterable[str]) -> Iterator[tuple[int, dict[str, Any] | None]]:
    """Yield each JSONL line number, using None for malformed/non-object rows."""
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            yield line_number, None
            continue
        yield line_number, event if isinstance(event, dict) else None


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        value = item.get("text") or item.get("input_text") or item.get(
            "output_text")
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def stable_message_ids(
        payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Read turn and message IDs from current and legacy payload locations."""
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if not isinstance(metadata, dict):
        metadata = {}
    turn_id = payload.get("turn_id") or metadata.get("turn_id")
    message_id = (payload.get("message_id") or metadata.get("message_id")
                  or payload.get("id"))
    return (
        str(turn_id) if turn_id else None,
        str(message_id) if message_id else None,
    )


def user_message_dedupe_key(payload: dict[str, Any], timestamp: Any,
                            content: str) -> tuple[str, str | None]:
    """Return the shared Desktop-message identity used by recovery and timeline."""
    turn_id, message_id = stable_message_ids(payload)
    if turn_id:
        return f"turn:{turn_id}", turn_id
    if message_id:
        return f"message:{message_id}", None
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"fallback:{timestamp}:{digest}", None


def tool_output_text(output: Any) -> str:
    """Flatten a tool output only for bounded metrics and evidence scanning."""
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if isinstance(item, dict):
                value = item.get("text") or item.get("output")
                if isinstance(value, str):
                    parts.append(value)
        return "\n".join(parts)
    if isinstance(output, dict):
        return json.dumps(output, ensure_ascii=False, sort_keys=True)
    return ""


def tool_output_summary(output: Any) -> tuple[str, str]:
    """Summarize explicit tool status without copying arbitrary output content."""
    text = tool_output_text(output)
    parsed: Any = output
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = None
    if not isinstance(parsed, dict):
        for line in reversed(text.splitlines()):
            if not line.lstrip().startswith("{"):
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                parsed = candidate
                break

    status = "returned"
    facts: list[str] = []
    if isinstance(parsed, dict):
        exit_code = parsed.get("exit_code")
        is_error = parsed.get("isError")
        if isinstance(exit_code, int):
            status = "success" if exit_code == 0 else "failed"
            facts.append(f"exit_code={exit_code}")
        elif is_error is True:
            status = "failed"
            facts.append("is_error=true")
        elif is_error is False:
            status = "success"
            facts.append("is_error=false")
        value = parsed.get("status")
        if isinstance(value, str) and value:
            facts.append(f"reported_status={value}")
        nested_output = parsed.get("output")
        if isinstance(nested_output, str):
            facts.append(f"result_chars={len(nested_output)}")
    if status == "returned":
        if text.startswith("Script completed\n"):
            status = "success"
            facts.append("wrapper=completed")
        elif text.startswith("Script failed\n"):
            status = "failed"
            facts.append("wrapper=failed")
    facts.append(f"output_chars={len(text)}")
    return status, ", ".join(facts)


def tool_call_id(payload: dict[str, Any], line_number: int) -> str:
    value = payload.get("call_id") or payload.get("id")
    return str(value) if value else f"line-{line_number}"


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n..."


def parse_call_input(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
        return parsed if isinstance(parsed, dict) else {"raw": raw}
    return {}


def js_string_field(source: str, field: str) -> str:
    """Extract a double-quoted field from the small JS wrappers in tool input."""
    match = re.search(
        rf"\b{re.escape(field)}\s*:\s*(\"(?:\\.|[^\"\\])*\")", source)
    if not match:
        return ""
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ""
    return value if isinstance(value, str) else ""


def exec_wrapper_summary(source: str) -> str:
    """Summarize nested tools.* calls without retaining the wrapper program."""
    tool_names = re.findall(r"\btools\.([A-Za-z0-9_]+)\s*\(", source)
    if not tool_names:
        return "exec"
    unique_names = list(dict.fromkeys(tool_names))
    if "exec_command" in unique_names:
        cmd = js_string_field(source, "cmd")
        summary = f"exec_command: {cmd}" if cmd else "exec_command"
    else:
        summary = ", ".join(unique_names[:3])
    if len(tool_names) > 1:
        summary += f" (+{len(tool_names) - 1} calls)"
    return summary


def command_from_call(payload: dict[str, Any]) -> str:
    name = payload.get("name") or payload.get("tool_name") or ""
    call_input = parse_call_input(payload.get("input"))
    if name.endswith("exec_command") or name == "exec_command":
        cmd = call_input.get("cmd")
        return str(cmd) if cmd else ""
    if name in {"apply_patch", "functions.apply_patch"}:
        return "apply_patch"
    if name in {"exec", "functions.exec"}:
        raw = payload.get("input")
        return exec_wrapper_summary(raw) if isinstance(raw, str) else "exec"
    return str(name)


def extract_context_blocks(text: str, source: str,
                           limit: int) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in CONTEXT_START_RE.finditer(text):
        start = match.start()
        if (match.group("legacy") and not re.match(
                r"<!--\s*context:[^\n]*-->\s*\n\s*---", text[start:])):
            continue
        next_match = CONTEXT_START_RE.search(text, match.end())
        end = next_match.start() if next_match else len(text)
        body = text[start:end].strip()
        blocks.append({
            "project": (match.group("standard")
                        or match.group("legacy")).strip(),
            "source": source,
            "text": truncate(body, limit),
        })
    return blocks


def append_limited(items: list[Any], value: Any, limit: int) -> None:
    items.append(value)
    overflow = len(items) - limit
    if overflow > 0:
        del items[:overflow]


def build_packet(path: Path, args: argparse.Namespace) -> str:
    meta: dict[str, Any] = {}
    user_message_candidates: list[dict[str, Any]] = []
    assistant_messages: list[dict[str, str]] = []
    commentary: list[dict[str, str]] = []
    tool_spans: dict[str, dict[str, Any]] = {}
    tool_order: list[str] = []
    aborts: list[str] = []
    context_blocks: list[dict[str, str]] = []
    path_counts: dict[str, int] = {}
    line_count = 0

    with path.open(encoding="utf-8") as handle:
        for line_count, event in iter_rollout_events(handle):
            if event is None:
                continue
            timestamp = str(event.get("timestamp") or "")
            event_type = event.get("type")
            payload = event.get("payload") if isinstance(
                event.get("payload"), dict) else {}

            if event_type == "session_meta":
                meta = payload

            if event_type == "turn_aborted":
                aborts.append(timestamp or f"line {line_count}")

            event_texts: list[str] = []

            if event_type == "event_msg":
                payload_type = payload.get("type")
                if payload_type == "user_message":
                    message = str(payload.get("message") or "")
                    # Desktop mirrors this event as a role=user response_item.
                    # Scan it for evidence, but use only response_item messages
                    # for the normalized recovery transcript.
                    event_texts.append(message)
                elif payload_type == "agent_message":
                    message = str(payload.get("message") or "")
                    append_limited(
                        commentary, {
                            "time": timestamp,
                            "text": truncate(message, args.max_text_chars),
                        }, args.max_messages)
                    event_texts.append(message)
                elif payload_type == "patch_apply_end":
                    call_id = str(payload.get("call_id") or "")
                    span = tool_spans.get(call_id) if call_id else None
                    if span is not None:
                        span["end_line"] = line_count
                        span["status"] = (
                            "success" if payload.get("success") is True else
                            "failed")
                        changes = payload.get("changes")
                        if isinstance(changes, dict):
                            span["result"] = f"changed_paths={len(changes)}"

            if event_type == "response_item":
                item_type = payload.get("type")
                if item_type == "message":
                    role = payload.get("role")
                    text = truncate(text_from_content(payload.get("content")),
                                    args.max_text_chars)
                    full_text = text_from_content(payload.get("content"))
                    if role == "user":
                        dedupe_key, turn_id = user_message_dedupe_key(
                            payload, timestamp, full_text)
                        user_message_candidates.append({
                            "dedupe_key": dedupe_key,
                            "time": timestamp,
                            "turn_id": turn_id,
                            "line_number": line_count,
                            "text": text,
                        })
                    elif role == "assistant":
                        append_limited(assistant_messages, {
                            "time": timestamp,
                            "text": text
                        }, args.max_messages)
                    event_texts.append(full_text)
                elif item_type in {"function_call", "custom_tool_call"}:
                    command = command_from_call(payload)
                    if command:
                        call_id = tool_call_id(payload, line_count)
                        if call_id not in tool_spans:
                            tool_order.append(call_id)
                        tool_spans[call_id] = {
                            "call_id": call_id,
                            "time": timestamp,
                            "name": str(
                                payload.get("name") or payload.get("tool_name")
                                or item_type),
                            "command": truncate(command, args.max_text_chars),
                            "start_line": line_count,
                            "end_line": line_count,
                            "status": "pending",
                            "result": "output_not_found",
                        }
                        event_texts.append(command)
                elif item_type in {
                        "function_call_output", "custom_tool_call_output"
                }:
                    output = payload.get("output")
                    call_id = str(payload.get("call_id") or "")
                    span = tool_spans.get(call_id) if call_id else None
                    if span is None:
                        synthetic_id = call_id or f"output-line-{line_count}"
                        tool_order.append(synthetic_id)
                        span = {
                            "call_id": synthetic_id,
                            "time": timestamp,
                            "name": "tool_output",
                            "command": "(call not found)",
                            "start_line": line_count,
                        }
                        tool_spans[synthetic_id] = span
                    span["end_line"] = line_count
                    span["status"], span["result"] = tool_output_summary(output)
                    output_text = tool_output_text(output)
                    if output_text:
                        event_texts.append(output_text)

            for text in event_texts:
                if "<turn_aborted>" in text:
                    aborts.append(timestamp or f"line {line_count}")

                for path_match in ABS_PATH_RE.findall(text):
                    path_counts[path_match] = path_counts.get(path_match,
                                                              0) + 1
                context_blocks.extend(
                    extract_context_blocks(
                        text, f"{timestamp or 'unknown'} line {line_count}",
                        args.max_context_chars))
                overflow = len(context_blocks) - args.max_context_blocks
                if overflow > 0:
                    del context_blocks[:overflow]

    grouped_user_messages: dict[str, dict[str, Any]] = {}
    for candidate in user_message_candidates:
        existing = grouped_user_messages.get(candidate["dedupe_key"])
        if existing is None:
            grouped_user_messages[candidate["dedupe_key"]] = {
                **candidate,
                "texts": [candidate["text"]],
            }
            continue
        if candidate["text"] and candidate["text"] not in existing["texts"]:
            existing["texts"].append(candidate["text"])
    user_messages = [{
        "time": row["time"],
        "text": "\n".join(text for text in row["texts"] if text),
    } for row in grouped_user_messages.values()][-args.max_messages:]
    recent_tool_spans = [
        tool_spans[call_id] for call_id in tool_order[-args.max_tool_calls:]
    ]

    lines = [
        "# Codex Rollout Recovery Packet",
        "",
        f"- rollout: `{path}`",
        f"- lines: {line_count}",
    ]
    if meta:
        lines.extend([
            f"- session_id: `{meta.get('session_id') or meta.get('id') or ''}`",
            f"- cwd: `{meta.get('cwd') or ''}`",
            f"- originator: {meta.get('originator') or ''}",
            f"- model: {meta.get('model') or meta.get('model_provider') or ''}",
        ])
    if aborts:
        lines.append(
            f"- turn_aborted: {len(aborts)} ({', '.join(aborts[-3:])})")

    def add_messages(title: str, rows: list[dict[str, str]]) -> None:
        if not rows:
            return
        lines.extend(["", f"## {title}"])
        for row in rows:
            lines.extend([
                "", f"### {row['time'] or 'unknown'}", "", row["text"]
                or "(empty)"
            ])

    add_messages("Recent User Messages", user_messages)
    add_messages("Recent Assistant Messages", assistant_messages)
    add_messages("Recent Commentary", commentary)

    if recent_tool_spans:
        lines.extend(["", "## Recent Tool Spans"])
        for row in recent_tool_spans:
            command = str(row["command"]).replace("`", "'")
            result = str(row["result"]).replace("`", "'")
            lines.append(
                f"- {row['time'] or 'unknown'} lines={row['start_line']}-{row['end_line']} "
                f"call={row['call_id']} status={row['status']} `{row['name']}`: "
                f"`{command}`; {result}"
            )

    if context_blocks:
        lines.extend(["", "## Context Blocks Found"])
        for block in context_blocks:
            lines.extend([
                "",
                f"### project={block['project']} from {block['source']}",
                "",
                "```markdown",
                block["text"],
                "```",
            ])

    if path_counts:
        lines.extend(["", "## Frequent Paths"])
        for path_text, count in sorted(path_counts.items(),
                                       key=lambda item:
                                       (-item[1], item[0]))[:args.max_paths]:
            lines.append(f"- {count}x `{path_text}`")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollout", help="Path to a Codex rollout JSONL file")
    parser.add_argument(
        "--thread-id",
        help=
        "Codex thread/session id to locate under sessions and archived_sessions"
    )
    parser.add_argument("--codex-home",
                        default=str(default_codex_home()),
                        help="Codex home directory")
    parser.add_argument("--max-messages", type=int, default=8)
    parser.add_argument("--max-tool-calls", type=int, default=30)
    parser.add_argument("--max-paths", type=int, default=25)
    parser.add_argument("--max-context-blocks", type=int, default=3)
    parser.add_argument("--max-text-chars", type=int, default=1200)
    parser.add_argument("--max-context-chars", type=int, default=12000)
    args = parser.parse_args()

    path = locate_rollout(
        Path(args.codex_home).expanduser(), args.rollout, args.thread_id)
    print(build_packet(path, args), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
