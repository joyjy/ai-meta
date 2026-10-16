#!/usr/bin/env python3
"""Regression tests for Codex session title inference."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_session_titles as titles

class LegacyEntryTest(unittest.TestCase):

    def test_write_mode_is_disabled_before_local_state_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp

            result = subprocess.run(
                [sys.executable, str(Path(titles.__file__)), "--current"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("client-native task rename", result.stderr)


if __name__ == "__main__":
    unittest.main()
