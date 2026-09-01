#!/usr/bin/env python3
"""Regression tests for the coding-conventions managed-block synchronizer."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "sync-conventions.sh"


class SyncConventionsTest(unittest.TestCase):

    def run_sync(
        self,
        agents_content: str,
        *,
        parent_content: str = "",
        runs: int = 1,
    ) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            agents = project / "AGENTS.md"
            agents.write_text(agents_content, encoding="utf-8")
            if parent_content:
                (project.parent / "AGENTS.md").write_text(
                    parent_content,
                    encoding="utf-8",
                )

            for _ in range(runs):
                proc = subprocess.run(
                    [str(SYNC), str(agents)],
                    cwd=ROOT,
                    env={**os.environ, "HOME": str(Path.home())},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, proc.returncode, proc.stderr)
            return agents.read_text(encoding="utf-8")

    def test_legacy_declaration_is_migrated_to_managed_block(self) -> None:
        content = self.run_sync(
            "# Project\n\n"
            "<!-- coding-conventions: cli -->\n"
            "<!-- coding-conventions:begin cli -->\n"
            "stale\n"
            "<!-- coding-conventions:end cli -->\n",
            parent_content=(
                "<!-- coding-conventions:begin general -->\n"
                "parent\n"
                "<!-- coding-conventions:end general -->\n"
            ),
        )

        self.assertNotIn("<!-- coding-conventions: cli -->", content)
        self.assertEqual(1, content.count("<!-- coding-conventions:begin cli -->"))
        self.assertNotIn("stale", content)

    def test_begin_marker_alone_declares_template(self) -> None:
        content = self.run_sync(
            "# Project\n\n"
            "<!-- coding-conventions:begin cli -->\n"
            "stale\n"
            "<!-- coding-conventions:end cli -->\n",
            parent_content=(
                "<!-- coding-conventions:begin general -->\n"
                "parent\n"
                "<!-- coding-conventions:end general -->\n"
            ),
            runs=2,
        )

        self.assertEqual(1, content.count("<!-- coding-conventions:begin cli -->"))
        self.assertNotIn("stale", content)

    def test_api_template_id_resolves_to_managed_template(self) -> None:
        content = self.run_sync(
            "# Project\n\n"
            "<!-- coding-conventions:begin api -->\n"
            "stale\n"
            "<!-- coding-conventions:end api -->\n",
            parent_content=(
                "<!-- coding-conventions:begin general -->\n"
                "parent\n"
                "<!-- coding-conventions:end general -->\n"
            ),
        )

        self.assertEqual(1, content.count("<!-- coding-conventions:begin api -->"))
        self.assertIn("Surface First", content)
        self.assertNotIn("stale", content)

    def test_missing_general_adds_block_without_separate_declaration(self) -> None:
        content = self.run_sync(
            "# Project\n\n"
            "<!-- coding-conventions:begin cli -->\n"
            "stale\n"
            "<!-- coding-conventions:end cli -->\n"
        )

        self.assertIn("<!-- coding-conventions:begin general -->", content)
        self.assertIn("<!-- coding-conventions:end general -->", content)
        self.assertNotIn("<!-- coding-conventions: general -->", content)
        self.assertLess(
            content.index("<!-- coding-conventions:begin general -->"),
            content.index("<!-- coding-conventions:begin cli -->"),
        )

    def test_node_test_kit_is_only_injected_when_explicitly_enabled(self) -> None:
        testing_only = self.run_sync(
            "# Project\n\n"
            "<!-- coding-conventions:begin testing -->\n"
            "stale\n"
            "<!-- coding-conventions:end testing -->\n",
            parent_content=(
                "<!-- coding-conventions:begin general -->\n"
                "parent\n"
                "<!-- coding-conventions:end general -->\n"
            ),
        )
        with_node_kit = self.run_sync(
            testing_only
            + "\n<!-- coding-conventions:begin node-test-kit -->\n"
            "stale\n"
            "<!-- coding-conventions:end node-test-kit -->\n",
            parent_content=(
                "<!-- coding-conventions:begin general -->\n"
                "parent\n"
                "<!-- coding-conventions:end general -->\n"
            ),
        )

        self.assertNotIn("Node-only CLI / server", testing_only)
        self.assertIn("Node-only CLI / server", with_node_kit)

    def test_personal_parent_only_includes_default_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            projects = home / "Documents" / "projects"
            projects.mkdir(parents=True)
            agents = projects / "AGENTS.md"
            agents.write_text(
                "<!-- coding-conventions:begin general -->\n"
                "stale\n"
                "<!-- coding-conventions:end general -->\n",
                encoding="utf-8",
            )
            skill_dir = home / ".ai" / "skills" / "coding-conventions"
            skill_dir.parent.mkdir(parents=True)
            skill_dir.symlink_to(
                ROOT / "skills" / "coding-conventions",
                target_is_directory=True,
            )

            proc = subprocess.run(
                [str(SYNC), str(agents)],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 通用个人偏好", content)
            self.assertIn("# Java 个人偏好", content)
            self.assertIn("# Review 个人偏好", content)
            self.assertNotIn("# IDaaS lintest MR Walkthrough", content)
            self.assertNotIn("# Pitfall Watch", content)
            self.assertNotIn("# Temporary Pitfalls", content)


if __name__ == "__main__":
    unittest.main()
