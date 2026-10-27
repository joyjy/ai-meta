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
            return [dict(zip(THREAD_FIELDS, row)) for row in rows]
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


def in_window(stamp: str | None, span: dict[str, Any]) -> bool:
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return False
    return span["start_ms"] <= moment.timestamp() * 1000 < span["end_ms"]


def skill_obligations(rollout: Path, span: dict[str, Any]) -> dict[str, Any] | None:
    """SKILL.md edited by apply_patch inside the window without any skill-verification begin in the thread."""
    edited: set[str] = set()
    begins: list[str] = []
    with rollout.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            payload = item.get("payload") or {}
            if item.get("type") != "response_item" or payload.get("type") not in {"custom_tool_call", "function_call"}:
                continue
            text = str(payload.get("input") or payload.get("arguments") or "")
            if BEGIN.search(text):
                begins.append(text)
            if in_window(item.get("timestamp"), span):
                edited.update(SKILL_EDIT.findall(text))
    # begin may name the skill through the repo path, a ~/.ai symlink or a relative path; match the skill directory name.
    missing = sorted(path for path in edited
                     if not any(f"/{Path(path).parent.name}" in text or f" {Path(path).parent.name}" in text
                                for text in begins))
    return {"edited_skills": sorted(edited), "missing_begin": missing} if edited else None


def unsettled_receipts(audits: Path) -> list[str]:
    return sorted(str(receipt) for receipt in audits.glob("*/receipt.json")
                  if not (receipt.parent / "settlement.json").exists())


def ledger(root: Path) -> dict[str, Any]:
    summary = skill_verification.status(argparse.Namespace(
        root=root, change_id=None, open_only=True, limit=10_000))
    changes = summary["changes"]
    return {
        "open_count": len(changes),
        # Drifted records can never validate; superseded ones only signal that a newer registration exists.
        "drifted_count": sum(1 for item in changes if item["source_drift"]),
        "superseded_count": sum(1 for item in changes if item["superseded_by"]),
        "open": [{"change_id": item["change_id"], "skill_id": item["skill_id"],
                  "verdict": item["evaluation"]["verdict"], "summary": item["summary"],
                  "source_drift": item["source_drift"], "superseded_by": item["superseded_by"],
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
        found = skill_obligations(rollout, span)
        if found and found["missing_begin"]:
            obligations.append({"thread_id": thread["id"], "obligation": "skill_verification_begin", **found})
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
        "limitations": ["SKILL.md edits made by shell commands instead of apply_patch are not detected",
                        "begin matching checks the edited skill directory name appears in a begin call of the same thread"],
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
