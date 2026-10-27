"""Local per-CLI usage log; method owned by coding-conventions patterns/cli-usage-observability.md."""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def log_path(cli: str) -> Path:
    root = Path(os.environ.get("AI_META_USAGE_DIR", Path.home() / ".ai" / "usage"))
    return root.expanduser() / f"{cli}.jsonl"


def record(cli: str, command: str, started: float, exit_code: int) -> None:
    """Append command name, time, duration and exit code only; failures never affect the CLI."""
    event = {
        "command": command,
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "duration_ms": round((time.monotonic() - started) * 1000),
        "exit_code": exit_code,
        "source": "unknown",
    }
    try:
        path = log_path(cli)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
    except OSError:
        pass


def summarize(cli: str, commands: list[str]) -> dict[str, Any]:
    rows = {name: {"calls": 0, "days": set(), "last_used": None, "exit_codes": Counter()}
            for name in commands}
    incomplete, times = 0, []
    path = log_path(cli)
    try:
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    except OSError:
        return {"available": False, "reason": "usage_log_unreadable", "path": str(path)}
    for line in lines:
        try:
            item = json.loads(line)
            row = rows[item["command"]]
            row["calls"] += 1
            row["days"].add(item["time"][:10])
            row["last_used"] = max(row["last_used"] or item["time"], item["time"])
            row["exit_codes"][str(item["exit_code"])] += 1
            times.append(item["time"])
        except (ValueError, KeyError, TypeError):
            incomplete += 1
    return {
        "available": True,
        "path": str(path),
        "window": "all retained local records",
        "started_at": min(times, default=None),
        "source": "unknown",
        "total_calls": sum(row["calls"] for row in rows.values()),
        "incomplete_records": incomplete,
        "commands": {name: {"calls": row["calls"], "active_days": len(row["days"]),
                            "last_used": row["last_used"], "exit_codes": dict(row["exit_codes"])}
                     for name, row in rows.items()},
        "limitations": "Calls before this log existed, failed log writes and interrupted runs are not counted.",
    }
