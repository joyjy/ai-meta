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
        automation = self.base / "automations" / "demo-auto"
        automation.mkdir(parents=True)
        (automation / "automation.toml").write_text('id = "demo-auto"\nmodel = "m-config"\nreasoning_effort = "low"\n')
        rows = [("edited", self.rollout("edited", [patch_call("/repo/skills/demo/SKILL.md")], automation_turns=True)),
                ("registered", self.rollout("registered", [
                    patch_call("/repo/skills/demo/SKILL.md"),
                    'tools.exec_command({cmd:"SV=~/.ai/scripts/skill-verification; $SV begin --skill /repo/skills/demo"})']))]
        for thread_id, rollout in rows:
            connection.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)",
                               (thread_id, "t", "/repo", "cli", "user", 0, str(rollout), DAY_MS, DAY_MS + 1000))
        connection.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?)",
                           ("older", "t", "/repo", "cli", "user", 0, "/missing", DAY_MS - 10**9, DAY_MS - 10**8))
        connection.commit()
        connection.close()
        self.claude_projects = self.base / "claude-projects"
        project = self.claude_projects / "-repo"
        (project / "c1" / "subagents").mkdir(parents=True)
        edit = {"type": "tool_use", "name": "Edit", "input": {"file_path": "/repo/skills/demo/SKILL.md"}}
        records = [{"type": "mode", "mode": "normal", "sessionId": "c1"},  # leading records carry no timestamp
                   {"type": "user", "timestamp": "2026-10-17T01:00:00Z", "turnOrigin": "human", "entrypoint": "cli",
                    "cwd": "/repo", "sessionId": "c1", "message": {"role": "user", "content": "edit the skill"}},
                   {"type": "assistant", "timestamp": "2026-10-17T01:00:05Z", "effort": "xhigh", "sessionId": "c1",
                    "message": {"model": "claude-x", "content": [edit]}},
                   {"type": "ai-title", "aiTitle": "edit demo skill", "sessionId": "c1"}]
        (project / "c1.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
        # Subagent transcripts live one level deeper and are not sessions of their own.
        (project / "c1" / "subagents" / "agent-a.jsonl").write_text(json.dumps(records[1]) + "\n")

    def rollout(self, name: str, inputs: list[str], automation_turns: bool = False) -> Path:
        path = self.base / f"{name}.jsonl"
        lines = [{"timestamp": "2026-10-17T03:00:00Z", "type": "response_item",
                  "payload": {"type": "custom_tool_call", "name": "exec", "input": text}} for text in inputs]
        if automation_turns:
            # An automation prompt, then the effort changes mid-thread; the repeated context must not add a segment.
            lines = [{"timestamp": "2026-10-17T02:00:00Z", "type": "response_item",
                      "payload": {"type": "message", "role": "user",
                                  "content": [{"type": "input_text", "text": "Automation ID: demo-auto"}]}},
                     *[{"timestamp": stamp, "type": "turn_context", "payload": {"model": "m-run", "effort": effort}}
                       for stamp, effort in [("2026-10-17T02:00:01Z", "low"), ("2026-10-17T02:30:00Z", "low"),
                                             ("2026-10-17T02:40:00Z", "medium")]],
                     *lines]
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
        return path

    def run_cli(self, *args: str) -> dict:
        env = dict(os.environ, AI_META_USAGE_DIR=str(self.base / "usage"))
        result = subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, env=env, check=True)
        return json.loads(result.stdout)

    def test_shell_alias_begin_does_not_hide_unregistered_skills(self) -> None:
        sys.path.insert(0, str(SCRIPT.parent))
        import daily_review_collect as collector
        command = "SV=~/.ai/scripts/skill-verification\nfor s in grill steelman piggyback; do $SV begin --skill skills/$s/SKILL.md; done"
        self.assertTrue(collector.has_begin_call(command))
        paths = {f"/repo/skills/{s}/SKILL.md" for s in ("grill", "steelman", "piggyback", "other")}
        self.assertEqual(["/repo/skills/other/SKILL.md"], collector.obligation(paths, [command])["missing_begin"])
        self.assertFalse(collector.has_begin_call("SV=some-other-command; $SV begin --skill skills/grill"))
        self.assertFalse(collector.has_begin_call("$SV begin --skill skills/grill"))

    def test_collect_reports_window_threads_receipts_and_missing_begin(self) -> None:
        packet = self.run_cli("collect", "--date", "2026-10-17", "--db", str(self.db),
                              "--codex-home", str(self.base), "--ledger-root", str(self.base / "ledger"),
                              "--audits", str(self.base / "audits"), "--claude-projects", str(self.claude_projects))
        self.assertEqual([("codex", "edited"), ("codex", "registered"), ("claude", "c1")],
                         [(t["client"], t["id"]) for t in packet["threads"]])
        self.assertEqual([str(self.base / "audits/open/receipt.json")], packet["audit_receipts_unsettled"])
        missing = {"obligation": "skill_verification_begin", "edited_skills": ["/repo/skills/demo/SKILL.md"],
                   "missing_begin": ["/repo/skills/demo/SKILL.md"]}
        self.assertEqual([{"thread_id": "edited", **missing}, {"thread_id": "c1", **missing}], packet["obligations"])
        claude = packet["threads"][2]
        self.assertEqual({"title": "edit demo skill", "cwd": "/repo", "entrypoints": ["cli"], "human_turns": 1,
                          "models": [{"model": "claude-x", "effort": "xhigh", "from": "2026-10-17T01:00:05Z"}]},
                         {k: claude[k] for k in ("title", "cwd", "entrypoints", "human_turns", "models")})
        self.assertEqual(0, packet["skill_verification"]["open_count"])
        edited = packet["threads"][0]
        self.assertEqual([{"model": "m-run", "effort": "low", "from": "2026-10-17T02:00:01Z"},
                          {"model": "m-run", "effort": "medium", "from": "2026-10-17T02:40:00Z"}], edited["models"])
        self.assertEqual({"id": "demo-auto", "configured": {"model": "m-config", "effort": "low"}}, edited["automation"])
        self.assertEqual([], packet["threads"][1]["models"])
        usage = self.run_cli("usage")
        self.assertEqual(1, usage["commands"]["collect"]["calls"])
        self.assertEqual(0, usage["commands"]["usage"]["calls"])


if __name__ == "__main__":
    unittest.main()
