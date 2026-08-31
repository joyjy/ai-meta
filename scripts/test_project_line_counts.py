#!/usr/bin/env python3
"""Regression tests for project-line-counts."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("project-line-counts")


class ProjectLineCountsTest(unittest.TestCase):

    def run_script(self, root: Path) -> str:
        result = subprocess.run(
            [str(SCRIPT), str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def test_binary_file_is_excluded_from_line_count_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.txt").write_text("one\ntwo\n", encoding="utf-8")
            (root / "generated-binary").write_bytes(
                b"#! /usr/bin/env escript\nPK\x03\x04\x00" + b"binary\n" * 20
            )

            output = self.run_script(root)

            self.assertIn("source.txt", output)
            self.assertNotIn("generated-binary", output)

    def test_git_repo_excludes_ignored_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("generated.txt\n", encoding="utf-8")
            (root / "source.txt").write_text("source\n", encoding="utf-8")
            (root / "generated.txt").write_text(
                "generated\n" * 20, encoding="utf-8"
            )
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "add", ".gitignore", "source.txt"],
                check=True,
            )

            output = self.run_script(root)

            self.assertIn("source.txt", output)
            self.assertNotIn("generated.txt", output)

    def test_git_repo_includes_untracked_non_ignored_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text("generated.txt\n", encoding="utf-8")
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            (root / "ordinary.txt").write_text("ordinary\n" * 2, encoding="utf-8")
            (root / "generated.txt").write_text("generated\n" * 20, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "add", ".gitignore", "tracked.txt"],
                check=True,
            )

            output = self.run_script(root)

            self.assertIn("tracked.txt", output)
            self.assertIn("ordinary.txt", output)
            self.assertNotIn("generated.txt", output)

    def test_generated_patch_is_excluded_from_source_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "overlay.ex").write_text("source\n" * 2, encoding="utf-8")
            (root / "generated.patch").write_text("patch\n" * 40, encoding="utf-8")

            output = self.run_script(root)

            self.assertIn("overlay.ex", output)
            self.assertNotIn("generated.patch", output)


if __name__ == "__main__":
    unittest.main()
