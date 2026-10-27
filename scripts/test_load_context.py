#!/usr/bin/env python3
"""Smoke tests for the load-context projection CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("load_context.py")

CONTEXT = """---
# context: project=demo; mainline=active; workstreams=1(active:side)
schema: context.v3
project: demo
goal: Demo goal
mainline:
  state: active
  summary: main summary
  doing:
    - main doing
  blocked: []
  next_steps: []
workstreams:
  side:
    state: active
    summary: side summary
    doing: []
    blocked: []
    next_step: side next
updated: '2026-10-27'
---

# demo context

## Mainline

### Doing

- main doing

### Critical Context

- kept `{kept}` and gone `{gone}` and durable `/Users/example/file.md`

## Workstreams

### side

### Doing

- side doing
"""


class LoadContextTest(unittest.TestCase):

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.kept = self.home / "kept.json"
        self.kept.write_text("{}", encoding="utf-8")
        contexts = self.home / ".ai" / "contexts"
        contexts.mkdir(parents=True)
        # TemporaryDirectory lives under a temp root, so both paths count as temporary outputs.
        (contexts / "demo.md").write_text(
            CONTEXT.format(kept=self.kept, gone=self.home / "gone.json"), encoding="utf-8")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, HOME=str(self.home), AI_META_USAGE_DIR=str(self.home / "usage"))
        return subprocess.run([sys.executable, str(SCRIPT), *args], text=True,
                              capture_output=True, check=False, env=env)

    def test_mainline_projection_omits_workstream_details(self) -> None:
        proc = self.run_cli("select", "demo")

        self.assertEqual(0, proc.returncode, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual("load-context.projection.v1", data["schema"])
        self.assertEqual({"by": "explicit"}, data["resolution"])
        self.assertEqual(["main doing"], data["selected"]["doing"])
        self.assertEqual([{"name": "side", "state": "active", "summary": "side summary"}],
                         data["workstreams"])
        self.assertIn("main doing", data["markdown"])
        self.assertNotIn("side doing", data["markdown"])
        self.assertEqual([{"path": str(self.kept), "status": "exists"},
                          {"path": str(self.home / "gone.json"), "status": "missing"}],
                         data["temporary_paths"])

    def test_cwd_resolution_selects_workstream_and_reports_missing_route(self) -> None:
        gtd = self.home / ".ai" / "scripts" / "gtd"
        gtd.parent.mkdir(parents=True)
        gtd.write_text("#!/bin/sh\necho '{\"status\": \"OK\", \"projects\": "
                       "[{\"abbr\": \"demo\", \"entry\": \"/p/index.md\"}]}'\n", encoding="utf-8")
        gtd.chmod(0o755)

        resolved = self.run_cli("select", "--cwd", str(self.home))
        side = self.run_cli("select", "demo:side")
        missing = self.run_cli("select", "demo:other")

        self.assertEqual(0, resolved.returncode, resolved.stderr)
        self.assertEqual({"by": "gtd project resolve", "entry": "/p/index.md"},
                         json.loads(resolved.stdout)["resolution"])
        self.assertEqual(0, side.returncode, side.stderr)
        side_data = json.loads(side.stdout)
        self.assertEqual("side next", side_data["selected"]["next_step"])
        self.assertIn("side doing", side_data["markdown"])
        self.assertNotIn("workstreams", side_data)
        self.assertEqual(2, missing.returncode)
        self.assertEqual("workstream_missing", json.loads(missing.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
