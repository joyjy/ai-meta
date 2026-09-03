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

HOME = Path.home()
LOAD_CONTEXT_LINK = "[$load-context](<maintenance-checkout>/skills/load-context/SKILL.md)"


class InferAbbrTest(unittest.TestCase):

    def test_cwd_wins_over_load_context_skill_link_path(self) -> None:
        row = {
            "cwd": str(HOME / "Documents" / "projects" / "service-meta-agent"),
            "title": "[amt][0529] sma",
            "first_user_message": LOAD_CONTEXT_LINK,
            "preview": LOAD_CONTEXT_LINK,
        }

        self.assertEqual("sma", titles.infer_abbr(row, []))

    def test_cwd_wins_over_old_wrong_title(self) -> None:
        row = {
            "cwd": str(HOME / "Documents" / "projects" / "service-meta-agent"),
            "title": "[amt][0529] sma",
        }

        self.assertEqual("sma", titles.infer_abbr(row, []))

    def test_explicit_load_context_arg_still_wins(self) -> None:
        row = {
            "cwd": str(HOME / "Documents" / "projects" / "service-meta-agent"),
            "first_user_message": "/load-context amt",
        }

        self.assertEqual("amt", titles.infer_abbr(row, []))

    def test_load_context_arg_wins_over_skill_link_path_with_extra_text(self) -> None:
        row = {
            "cwd": str(HOME / "Documents" / "projects"),
            "first_user_message": f"{LOAD_CONTEXT_LINK} idaas 历史分线都迁移下",
            "preview": f"{LOAD_CONTEXT_LINK} idaas 历史分线都迁移下",
        }

        self.assertEqual("idaas", titles.infer_abbr(row, []))

    def test_generic_projects_cwd_does_not_mask_user_text(self) -> None:
        row = {
            "cwd": str(HOME / "Documents" / "projects"),
            "first_user_message": "看下 ./iam-idaas-auth-api 的 MR",
        }

        self.assertEqual("idaas", titles.infer_abbr(row, []))

    def test_daily_note_summary_strips_timeline_prefix(self) -> None:
        self.assertEqual(
            "ai-meta 去除源码内本机绝对路径、提交并推送 b6b600d",
            titles.daily_note_summary(
                "[14:00-14:22] ai-meta 去除源码内本机绝对路径、提交并推送 b6b600d"
            ),
        )

    def test_title_can_use_daily_note_summary(self) -> None:
        row = {
            "cwd": str(titles.REPO_ROOT),
            "created_at": "2026-06-24T06:20:00Z",
        }

        self.assertEqual(
            "[amt][0624] ai-meta 去除源码内本机绝对路径、提交并推送 b6b600d",
            titles.title_for(
                row,
                [],
                "- [14:00-14:22] ai-meta 去除源码内本机绝对路径、提交并推送 b6b600d",
            ),
        )


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
