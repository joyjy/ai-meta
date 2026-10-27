#!/usr/bin/env python3
"""Main-path regression for appending a Claude Code session title."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "claude-session-title"


class SessionTitleTest(unittest.TestCase):
    def run_cli(self, projects: Path, session_id: str, title: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id, AI_META_USAGE_DIR=str(projects / "usage"))
        return subprocess.run([str(SCRIPT), "set", "--title", title, "--projects", str(projects)],
                              capture_output=True, text=True, env=env)

    def test_appends_custom_title_to_the_exact_session_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            projects = Path(temporary)
            current = projects / "-repo" / "abc.jsonl"
            other = projects / "-repo" / "other.jsonl"
            current.parent.mkdir()
            current.write_text('{"type":"ai-title","aiTitle":"load-context amt"}\n')
            other.write_text("")
            result = self.run_cli(projects, "abc", "[amt][1018]  标题")
            self.assertEqual(0, result.returncode, result.stderr)
            last = json.loads(current.read_text().splitlines()[-1])
            self.assertEqual({"type": "custom-title", "customTitle": "[amt][1018] 标题", "sessionId": "abc"}, last)
            self.assertEqual("", other.read_text())
            self.assertNotEqual(0, self.run_cli(projects, "missing", "x").returncode)


if __name__ == "__main__":
    unittest.main()
