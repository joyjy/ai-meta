#!/usr/bin/env python3
"""Portable distribution tests for the route-context prompt hook."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT.parents[1]
HOOK = PLUGIN_ROOT / "hooks/route-context-user-prompt.js"


class PortableRouteContextHookTest(unittest.TestCase):

    def run_hook(self, prompt: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **os.environ,
                "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
                "AI_META_ROUTE_CONTEXT_PATH": str(REPO_ROOT / "route-context.json"),
                "AI_META_ROUTE_CONTEXT_LOCAL_PATH": str(
                    Path(tmp) / "route-context.local.json"
                ),
            }
            proc = subprocess.run(
                ["node", str(HOOK)],
                input=json.dumps({"prompt": prompt, "cwd": str(REPO_ROOT)}),
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
        self.assertEqual(0, proc.returncode, proc.stderr)
        return json.loads(proc.stdout)

    def test_injects_portable_route(self) -> None:
        output = self.run_hook("运行 ./gradlew test")

        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn('"id": "gradle-wrapper-local-cache"', context)

    def test_ordinary_chat_stays_empty(self) -> None:
        self.assertEqual({}, self.run_hook("普通聊天，不涉及工具路由"))


if __name__ == "__main__":
    unittest.main()
