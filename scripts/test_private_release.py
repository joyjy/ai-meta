#!/usr/bin/env python3
"""Smoke tests for the sanitized private release builder."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts/private-release"


class PrivateReleaseTest(unittest.TestCase):

    def test_builds_distribution_role_and_omits_local_history(self) -> None:
        root_role = json.loads(
            (ROOT / ".ai-meta-repo-role.json").read_text(encoding="utf-8")
        )
        if root_role["role"] == "distribution":
            checked = subprocess.run(
                [str(COMMAND), "check", str(ROOT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, checked.returncode, checked.stderr)
            return

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ai-meta"
            built = subprocess.run(
                [str(COMMAND), "build", str(target), "--allow-dirty"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, built.returncode, built.stderr)
            role = json.loads(
                (target / ".ai-meta-repo-role.json").read_text(encoding="utf-8")
            )
            self.assertEqual("distribution", role["role"])
            self.assertFalse((target / "agent-frictions-archive.md").exists())
            self.assertFalse(
                (target / "manual/ai-external-memory-sharing.md").exists()
            )
            self.assertFalse((target / ".pytest_cache").exists())
            self.assertFalse((target / ".DS_Store").exists())
            self.assertTrue((target / "release/private/route-context.json").exists())
            self.assertTrue((target / "scripts/private-release").exists())
            self.assertIn(
                "disable-model-invocation: true",
                (target / "skills/agent-assignment/SKILL.md").read_text(encoding="utf-8").split("---", 2)[1],
            )
            self.assertIn(
                "allow_implicit_invocation: false",
                (target / "skills/agent-assignment/agents/openai.yaml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "`agent-assignment` 默认不自动调用",
                (target / "instructions.md").read_text(encoding="utf-8"),
            )

            checked = subprocess.run(
                [str(COMMAND), "check", str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, checked.returncode, checked.stderr)

            nested_target = Path(tmp) / "must-not-build"
            rejected = subprocess.run(
                [str(target / "scripts/private-release"), "build", str(nested_target)],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("maintenance checkout", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
