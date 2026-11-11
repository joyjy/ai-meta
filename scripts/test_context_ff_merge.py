#!/usr/bin/env python3
"""Regression tests for context_ff_merge.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT = Path(__file__).with_name("context_ff_merge.py")


class ContextFFMergeTest(unittest.TestCase):

    def setUp(self) -> None:
        usage = tempfile.TemporaryDirectory()
        self.addCleanup(usage.cleanup)
        self.env = dict(os.environ, AI_META_USAGE_DIR=usage.name)

    def ff(self, goal: str = "Ship the narrow change") -> dict:
        return {
            "output_target": "context",
            "goal": goal,
            "cwd": "/tmp/project",
            "scope": {
                "include": ["a.py"]
            },
            "acceptance": ["done"],
            "blocking_questions": [],
            "ready_for_dispatch": True,
            "dispatch_target": "codex",
        }

    def run_script(self, context_dir: Path,
                   ff_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "amt",
                "--context-dir",
                str(context_dir),
                "--ff-file",
                str(ff_path),
                "--date",
                "2026-07-02",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=self.env,
        )

    def run_clear(self,
                  context_dir: Path,
                  goal: str,
                  route: str = "mainline") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "amt",
                "--context-dir",
                str(context_dir),
                "--clear-completed",
                "--expect-goal",
                goal,
                "--route",
                route,
                "--date",
                "2026-07-11",
            ],
            text=True,
            capture_output=True,
            check=False,
            env=self.env,
        )

    def write_ff(self, root: Path, ff: dict | None = None) -> Path:
        path = root / "ff.json"
        path.write_text(json.dumps({"ff": ff or self.ff()},
                                   ensure_ascii=False),
                        encoding="utf-8")
        return path

    def test_missing_context_creates_minimal_mainline_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context_dir = root / "contexts"

            proc = self.run_script(context_dir, self.write_ff(root))

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = (context_dir / "amt.md").read_text(encoding="utf-8")
            self.assertTrue(context.startswith("---\n# context: project=amt;"))
            self.assertIn("schema: context.v3", context)
            self.assertIn("project: amt", context)
            self.assertIn("next_steps:", context)
            self.assertIn("goal: Ship the narrow change", context)

    def test_existing_mainline_gets_new_workstream_without_losing_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context_dir = root / "contexts"
            context_dir.mkdir()
            (context_dir / "amt.md").write_text(
                """---
# context: project=amt; mainline=active; workstreams=1(active:other)
schema: context.v3
project: amt
goal: Existing context.
mainline:
  state: active
  summary: keep summary
  doing: [keep doing]
  blocked: []
  next_steps:
  - ff: {goal: Old goal}
workstreams:
  ff-1: {state: active, summary: preserve me, doing: [], blocked: [], next_step: keep this}
updated: 2026-07-01
---

# amt Context
""",
                encoding="utf-8")

            proc = self.run_script(context_dir,
                                   self.write_ff(root, self.ff("New goal")))

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = (context_dir / "amt.md").read_text(encoding="utf-8")
            self.assertIn("goal: New goal", context)
            self.assertIn("goal: Old goal", context)
            self.assertIn("summary: preserve me", context)
            self.assertIn("next_step: keep this", context)
            self.assertIn("  doing:\n    - keep doing", context)
            self.assertIn("route ff-2", proc.stdout)
            self.assertIn("active:ff-2", context)
            # Retry the same CLI request: no duplicate branch or changed state.
            retry = self.run_script(context_dir,
                                    self.write_ff(root, self.ff("New goal")))
            self.assertEqual(0, retry.returncode, retry.stderr)
            self.assertIn("route ff-2", retry.stdout)
            self.assertEqual(yaml.safe_load(context.split("---")[1]),
                             yaml.safe_load((context_dir / "amt.md").read_text().split("---")[1]))

    def test_malformed_context_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context_dir = root / "contexts"
            context_dir.mkdir()
            context_path = context_dir / "amt.md"
            original = "---\n# context: project=amt; mainline=active; workstreams=0()\n"
            context_path.write_text(original, encoding="utf-8")

            proc = self.run_script(context_dir, self.write_ff(root))

            self.assertEqual(1, proc.returncode)
            self.assertIn("frontmatter", proc.stderr)
            self.assertEqual(original,
                             context_path.read_text(encoding="utf-8"))

    def test_clear_completed_mainline_ff_preserves_other_next_steps(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp)
            context_path = context_dir / "amt.md"
            context_path.write_text(
                """---
# context: project=amt; mainline=active; workstreams=0()
schema: context.v3
project: amt
mainline:
  state: active
  doing: []
  blocked: []
  next_steps:
  - ff:
      goal: Completed goal
  - note: preserve me
workstreams: {}
updated: 2026-07-10
---

# amt Context
""",
                encoding="utf-8")

            proc = self.run_clear(context_dir, "Completed goal")

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = context_path.read_text(encoding="utf-8")
            self.assertNotIn("goal: Completed goal", context)
            self.assertIn("note: preserve me", context)
            self.assertIn("state: active", context)

    def test_clear_completed_workstream_ff_removes_empty_route(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp)
            context_path = context_dir / "amt.md"
            context_path.write_text(
                """---
# context: project=amt; mainline=idle; workstreams=1(active:forum)
schema: context.v3
project: amt
mainline: {state: idle, doing: [], blocked: [], next_steps: []}
workstreams:
  forum:
    state: active
    doing: []
    blocked: []
    next_step: {ff: {goal: Completed forum goal}}
updated: 2026-07-10
---

# amt Context

## Mainline

Keep this.

## Workstreams

### forum

Completed recovery details.
""",
                encoding="utf-8")

            proc = self.run_clear(context_dir, "Completed forum goal", "forum")

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = context_path.read_text(encoding="utf-8")
            self.assertNotIn("goal: Completed forum goal", context)
            self.assertNotIn("forum:", context)
            self.assertNotIn("## Workstreams", context)
            self.assertIn("## Mainline\n\nKeep this.", context)
            self.assertIn("workstreams=0()", context)

    def test_clear_completed_workstream_ff_preserves_nonempty_route(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp)
            context_path = context_dir / "amt.md"
            context_path.write_text(
                """---
# context: project=amt; mainline=idle; workstreams=1(active:forum)
schema: context.v3
project: amt
mainline: {state: idle, doing: [], blocked: [], next_steps: []}
workstreams:
  forum:
    state: active
    doing: [Preserve this work]
    blocked: []
    next_step: {ff: {goal: Completed forum goal}}
updated: 2026-07-10
---

# amt Context

## Workstreams

### forum

Preserve these details.
""",
                encoding="utf-8")

            proc = self.run_clear(context_dir, "Completed forum goal", "forum")

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = context_path.read_text(encoding="utf-8")
            self.assertNotIn("goal: Completed forum goal", context)
            self.assertIn("- Preserve this work", context)
            self.assertIn("next_step: null", context)
            self.assertIn("### forum", context)

    def test_clear_completed_workstream_ff_preserves_other_detail_section(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp)
            context_path = context_dir / "amt.md"
            context_path.write_text(
                """---
# context: project=amt; mainline=idle; workstreams=2(active:forum, parked:other)
schema: context.v3
project: amt
mainline: {state: idle, doing: [], blocked: [], next_steps: []}
workstreams:
  forum:
    state: active
    doing: []
    blocked: []
    next_step: {ff: {goal: Completed forum goal}}
  other: {state: parked, doing: [], blocked: [], next_step: null}
updated: 2026-07-10
---

## Workstreams
### forum
### Critical Context
Remove target details.
### other
### Critical Context
Preserve unrelated details.
""",
                encoding="utf-8")

            proc = self.run_clear(context_dir, "Completed forum goal", "forum")

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = context_path.read_text(encoding="utf-8")
            self.assertNotIn("### forum", context)
            self.assertNotIn("Remove target details.", context)
            self.assertIn("### other", context)
            self.assertIn("Preserve unrelated details.", context)
            self.assertIn("workstreams=1(parked:other)", context)

    def test_clear_completed_ff_refuses_goal_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context_dir = root / "contexts"
            self.assertEqual(
                0,
                self.run_script(context_dir, self.write_ff(root)).returncode,
            )
            context_path = context_dir / "amt.md"
            original = context_path.read_text(encoding="utf-8")

            proc = self.run_clear(context_dir, "Different goal")

            self.assertEqual(1, proc.returncode)
            self.assertIn("found 0", proc.stderr)
            self.assertEqual(original,
                             context_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
