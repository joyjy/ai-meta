#!/usr/bin/env python3
"""Extract objective user-message timestamps from a Codex rollout."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from save_context_recover import (default_codex_home, iter_rollout_events,
                                  locate_rollout, stable_message_ids,
                                  text_from_content, user_message_dedupe_key)

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


def build_timeline(path: Path,
                   requested_thread_id: str | None = None,
                   *,
                   include_points: bool = False) -> dict[str, Any]:
    """Build the stable timeline schema from role=user response messages."""
    timezone, timezone_name = local_timezone()
    thread_id = requested_thread_id
    candidates: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, event in iter_rollout_events(handle):
            if event is None:
                continue
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Extract deduplicated role=user timestamps from a Codex "
                     "rollout as stable local-time JSON. checkpoint_at equals "
                     "the last deduplicated user timestamp; no activity or "
                     "work-duration inference is performed. Summary output is "
                     "the default; control-only load-context turns are "
                     "excluded."))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--rollout", help="Path to a Codex rollout JSONL file")
    source.add_argument(
        "--thread-id",
        help=
        "Codex thread/session id to locate under sessions and archived_sessions",
    )
    parser.add_argument(
        "--codex-home",
        default=str(default_codex_home()),
        help="Codex home directory used with --thread-id",
    )
    parser.add_argument(
        "--include-points",
        action="store_true",
        help="Include every deduplicated user timestamp for diagnostics",
    )
    args = parser.parse_args()

    try:
        path = locate_rollout(
            Path(args.codex_home).expanduser(), args.rollout, args.thread_id)
        timeline = build_timeline(path,
                                  args.thread_id,
                                  include_points=args.include_points)
    except TimelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(timeline, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
