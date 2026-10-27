#!/usr/bin/env python3
"""Main-path regression for the daily-review fact collector CLI."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "daily-review-collect"
DAY_MS = 1792166400000  # 2026-10-17 00:00 Asia/Shanghai


def patch_call(path: str) -> str:
    # Shape of a Codex exec call that applies a patch; the patch text is a JS string literal.
    return 'text(await tools.apply_patch("*** Begin Patch\\n*** Update File: ' + path + '\\n@@\\n-a\\n+b\\n*** End Patch"));'


class CollectTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        (self.base / "ledger" / "changes").mkdir(parents=True)
        for name, settled in [("open", False), ("done", True)]:
            audit = self.base / "audits" / name
            audit.mkdir(parents=True)
            (audit / "receipt.json").write_text("{}")
            if settled:
                (audit / "settlement.json").write_text("{}")
        self.db = self.base / "state.sqlite"
        connection = sqlite3.connect(self.db)
        connection.execute("CREATE TABLE threads (id, title, cwd, source, thread_source, archived, "
                           "rollout_path, created_at_ms, updated_at_ms)")
        rows = [("edited", self.rollout("edited", [patch_call("/repo/skills/demo/SKILL.md")])),
                ("registered", self.rollout("registered", [
                    patch_call("/repo/skills/demo/SKILL.md"),
                    'tools.exec_command({cmd:"skill-verification begin --skill /repo/skills/demo"})']))]
        for thread_id, rollout in rows:
            connection.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)",
                               (thread_id, "t", "/repo", "cli", "user", 0, str(rollout), DAY_MS, DAY_MS + 1000))
        connection.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)",
                           ("older", "t", "/repo", "cli", "user", 0, "/missing", DAY_MS - 10**9, DAY_MS - 10**8))
        connection.commit()
        connection.close()

    def rollout(self, name: str, inputs: list[str]) -> Path:
        path = self.base / f"{name}.jsonl"
        lines = [{"timestamp": "2026-10-17T03:00:00Z", "type": "response_item",
                  "payload": {"type": "custom_tool_call", "name": "exec", "input": text}} for text in inputs]
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
        return path

    def run_cli(self, *args: str) -> dict:
        env = dict(os.environ, AI_META_USAGE_DIR=str(self.base / "usage"))
        result = subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, env=env, check=True)
        return json.loads(result.stdout)

    def test_collect_reports_window_threads_receipts_and_missing_begin(self) -> None:
        packet = self.run_cli("collect", "--date", "2026-10-17", "--db", str(self.db),
                              "--codex-home", str(self.base), "--ledger-root", str(self.base / "ledger"),
                              "--audits", str(self.base / "audits"))
        self.assertEqual(["edited", "registered"], [t["id"] for t in packet["threads"]])
        self.assertEqual([str(self.base / "audits/open/receipt.json")], packet["audit_receipts_unsettled"])
        self.assertEqual([{"thread_id": "edited", "obligation": "skill_verification_begin",
                           "edited_skills": ["/repo/skills/demo/SKILL.md"],
                           "missing_begin": ["/repo/skills/demo/SKILL.md"]}], packet["obligations"])
        self.assertEqual(0, packet["skill_verification"]["open_count"])
        usage = self.run_cli("usage")
        self.assertEqual(1, usage["commands"]["collect"]["calls"])
        self.assertEqual(0, usage["commands"]["usage"]["calls"])


if __name__ == "__main__":
    unittest.main()
