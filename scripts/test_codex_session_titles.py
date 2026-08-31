#!/usr/bin/env python3
"""Regression tests for Codex session title inference."""

from __future__ import annotations

from datetime import datetime
import os
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


class BackupRetentionTest(unittest.TestCase):

    def test_prune_old_backups_keeps_only_recent_week(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_backup = Path(tmp) / "state_5.sqlite.20260601-120000.bak"
            fresh_backup = Path(tmp) / "state_5.sqlite.20260622-120000.bak"
            ignored = Path(tmp) / "notes.txt"
            old_backup.write_text("old")
            fresh_backup.write_text("fresh")
            ignored.write_text("ignored")

            now = datetime(2026, 6, 22, 12, 0, 0)
            os.utime(old_backup, (now.timestamp() - 8 * 24 * 60 * 60, now.timestamp() - 8 * 24 * 60 * 60))
            os.utime(fresh_backup, (now.timestamp() - 6 * 24 * 60 * 60, now.timestamp() - 6 * 24 * 60 * 60))
            os.utime(ignored, (now.timestamp() - 30 * 24 * 60 * 60, now.timestamp() - 30 * 24 * 60 * 60))

            previous_backup_dir = titles.BACKUP_DIR
            try:
                titles.BACKUP_DIR = Path(tmp)

                self.assertEqual(1, titles.prune_old_backups(now))
                self.assertFalse(old_backup.exists())
                self.assertTrue(fresh_backup.exists())
                self.assertTrue(ignored.exists())
            finally:
                titles.BACKUP_DIR = previous_backup_dir


if __name__ == "__main__":
    unittest.main()
