#!/usr/bin/env python3
"""Set the current Claude Code session title by appending the client's custom-title transcript record.

The record shape mirrors what `/rename` writes in Claude Code 2.1.x; it is an internal format and may
stop taking effect after a client update. Run it when the session is about to end: the running UI keeps
its cached title until the session is resumed or the session list is reopened.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_usage  # noqa: E402

CLI = "claude-session-title"
COMMANDS = ["set", "usage"]


def transcript(session_id: str, projects: Path) -> Path:
    matches = sorted(projects.glob(f"*/{session_id}.jsonl"))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one transcript for session {session_id}, found {len(matches)}")
    return matches[0]


def set_title(args: argparse.Namespace) -> dict[str, Any]:
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session_id:
        raise ValueError("CLAUDE_CODE_SESSION_ID is not set; run inside a Claude Code session")
    title = " ".join(args.title.split())
    if not title:
        raise ValueError("title is empty")
    path = transcript(session_id, args.projects)
    line = json.dumps({"type": "custom-title", "customTitle": title, "sessionId": session_id},
                      ensure_ascii=False) + "\n"
    # One O_APPEND write keeps the record whole next to the client's own appends.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    latest = None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if '"custom-title"' in raw:
                try:
                    latest = json.loads(raw).get("customTitle")
                except ValueError:
                    continue
    if latest != title:
        raise ValueError("read-back did not find the new custom-title record")
    return {"session_id": session_id, "transcript": str(path), "title": title, "readback": "matched"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("set", help="append a custom-title record for the current session")
    run.add_argument("--title", required=True)
    run.add_argument("--projects", type=Path, default=Path.home() / ".claude/projects")
    run.set_defaults(handler=set_title)
    usage = commands.add_parser("usage", help="local call statistics")
    usage.set_defaults(handler=lambda _args: cli_usage.summarize(CLI, COMMANDS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started, code = time.monotonic(), 0
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        code = 2
    cli_usage.record(CLI, args.command, started, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
