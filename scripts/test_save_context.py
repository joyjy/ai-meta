#!/usr/bin/env python3
"""Regression tests for save_context.py."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("save_context.py")
sys.path.insert(0, str(SCRIPT.parent))

import save_context  # noqa: E402


class ContextInputTest(unittest.TestCase):

    def valid_context(self, project: str = "amt") -> str:
        return f"""---
# context: project={project}; mainline=active; workstreams=0(); next=mainline
schema: context.v2
project: {project}
goal: Test context.
mainline:
  state: active
  summary: null
  doing: []
  blocked: []
  next_steps: []
workstreams: {{}}
next_route: mainline
updated: 2026-07-02
---

# {project} Context
"""

    def run_script(self,
                   home: Path,
                   *args: str,
                   input_text: str = "") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_context_stdin_writes_context_without_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context = self.valid_context()

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=context)

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(context, (home / ".ai" / "contexts" /
                                       "amt.md").read_text(encoding="utf-8"))
            self.assertIn("wrote", proc.stdout)

    def test_context_file_dash_reads_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context = self.valid_context()

            proc = self.run_script(home,
                                   "amt",
                                   "--context-file",
                                   "-",
                                   "--skip-timeline",
                                   input_text=context)

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(context, (home / ".ai" / "contexts" /
                                       "amt.md").read_text(encoding="utf-8"))

    def test_malformed_context_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context_path = home / ".ai" / "contexts" / "amt.md"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(self.valid_context(), encoding="utf-8")
            malformed = """---
# context: project=amt; mainline=active; workstreams=0(); next=mainline
schema: context.v2
project: amt
mainline:
  state: active
"""

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=malformed)

            self.assertEqual(2, proc.returncode)
            self.assertIn("frontmatter delimiters", proc.stderr)
            self.assertEqual(self.valid_context(),
                             context_path.read_text(encoding="utf-8"))

    def test_context_project_must_match_abbr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)

            proc = self.run_script(home,
                                   "gtd",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=self.valid_context("amt"))

            self.assertEqual(2, proc.returncode)
            self.assertIn("does not match abbr", proc.stderr)
            self.assertFalse((home / ".ai" / "contexts" /
                              "gtd.md").exists())

    def test_route_index_next_must_match_next_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            inconsistent = self.valid_context().replace("next=mainline",
                                                        "next=none")

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=inconsistent)

            self.assertEqual(2, proc.returncode)
            self.assertIn("index next does not match", proc.stderr)

    def test_removed_route_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            legacy = self.valid_context().replace(
                "next_route: mainline",
                "selected_route: mainline\nactive_route: mainline",
            )

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=legacy)

            self.assertEqual(2, proc.returncode)
            self.assertIn("removed route key(s)", proc.stderr)
            self.assertFalse((home / ".ai" / "contexts" /
                              "amt.md").exists())

    def test_next_route_must_name_a_known_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            invalid = self.valid_context().replace("next_route: mainline",
                                                   "next_route: [forum]")

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=invalid)

            self.assertEqual(2, proc.returncode)
            self.assertIn("next_route ['forum'] does not exist", proc.stderr)

    def test_fallback_frontmatter_parser_accepts_empty_workstreams(
            self) -> None:
        _, frontmatter = save_context.split_context_frontmatter(
            self.valid_context())

        parsed = save_context.fallback_parse_frontmatter(frontmatter)

        self.assertEqual("context.v2", parsed["schema"])
        self.assertEqual({}, parsed["workstreams"])

    def test_empty_context_stdin_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context_path = home / ".ai" / "contexts" / "amt.md"
            context_path.parent.mkdir(parents=True)
            context_path.write_text("# existing\n", encoding="utf-8")

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text="")

            self.assertEqual(2, proc.returncode)
            self.assertIn("context input is empty", proc.stderr)
            self.assertEqual("# existing\n",
                             context_path.read_text(encoding="utf-8"))

    def test_allow_empty_context_stdin_writes_empty_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context_path = home / ".ai" / "contexts" / "amt.md"
            context_path.parent.mkdir(parents=True)
            context_path.write_text("# existing\n", encoding="utf-8")

            proc = self.run_script(home,
                                   "amt",
                                   "--context-stdin",
                                   "--allow-empty",
                                   "--skip-timeline",
                                   input_text="")

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual("", context_path.read_text(encoding="utf-8"))

    def test_workstream_save_merges_only_explicit_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context_path = home / ".ai" / "contexts" / "amt.md"
            context_path.parent.mkdir(parents=True)
            context_path.write_text(self.valid_context().replace(
                "workstreams: {}", """workstreams:
  forum:
    state: active
    summary: Old forum
    doing: [old]
    blocked: []
    next_step: old
  other:
    state: parked
    summary: Preserve other
    doing: []
    blocked: []
    next_step: keep""").replace(
                "workstreams=0()", "workstreams=2(active:forum, parked:other)"
            ).replace("# amt Context", """# amt Context

## Mainline

keep mainline details

## Workstreams

### forum

old forum details

### other

preserve other details"""),
                                    encoding="utf-8")
            payload = """schema: context.workstream.v1
state: blocked
summary: Updated forum
doing:
  - finish writer
blocked:
  - missing trigger
next_step: validate writer
details: |
  ### Doing

  - finish writer

  ### Blocked

  - missing trigger
"""

            proc = self.run_script(home,
                                   "amt:forum",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text=payload)

            self.assertEqual(0, proc.returncode, proc.stderr)
            context = context_path.read_text(encoding="utf-8")
            _, frontmatter = save_context.split_context_frontmatter(context)
            parsed = save_context.parse_frontmatter(frontmatter)
            self.assertEqual("Updated forum",
                             parsed["workstreams"]["forum"]["summary"])
            self.assertEqual("Preserve other",
                             parsed["workstreams"]["other"]["summary"])
            self.assertEqual("active", parsed["mainline"]["state"])
            self.assertIn("keep mainline details", context)
            self.assertIn("preserve other details", context)
            self.assertIn("finish writer", context)
            self.assertNotIn("old forum details", context)

    def test_invalid_workstream_payload_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            context_path = home / ".ai" / "contexts" / "amt.md"
            context_path.parent.mkdir(parents=True)
            original = self.valid_context()
            context_path.write_text(original, encoding="utf-8")

            proc = self.run_script(home,
                                   "amt:forum",
                                   "--context-stdin",
                                   "--skip-timeline",
                                   input_text="state: active\n")

            self.assertEqual(2, proc.returncode)
            self.assertIn("missing required key", proc.stderr)
            self.assertEqual(original,
                             context_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
