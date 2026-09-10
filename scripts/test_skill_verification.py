#!/usr/bin/env python3
"""Regression tests for the revision-bound skill verification ledger."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skill_verification as verification


class SkillVerificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.repo = base / "repo"
        self.root = base / "runtime"
        self.skill = self.repo / "skills" / "demo" / "SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("# Demo\n\nUse the demo behavior.\n", encoding="utf-8")
        self.git("init")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "add demo skill")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def begin(self, required_samples: int = 0) -> dict:
        return verification.begin(argparse.Namespace(
            root=self.root,
            skill=str(self.skill),
            summary="change demo behavior",
            acceptance=["the demo route is selected"],
            artifact=[],
            required_samples=required_samples,
            at="2026-09-08T01:00:00Z",
        ))

    def check(self, change_id: str, status: str = "passed",
              evidence_ref: str = "cmd:unit-regression") -> dict:
        return verification.record_check(argparse.Namespace(
            root=self.root,
            change_id=change_id,
            name="unit-regression",
            status=status,
            evidence_ref=evidence_ref,
            at="2026-09-08T01:01:00Z",
        ))

    def load(self, change_id: str, path: Path | None = None) -> dict:
        return verification.record_load(argparse.Namespace(
            root=self.root,
            change_id=change_id,
            client="codex",
            session_id="session-1",
            loaded_path=str(path or self.skill),
            evidence_ref="task:session-1",
            at="2026-09-08T01:02:00Z",
        ))

    def sample(self, change_id: str, load_id: str, result: str,
               evidence_ref: str) -> dict:
        return verification.record_sample(argparse.Namespace(
            root=self.root,
            change_id=change_id,
            load_id=load_id,
            result=result,
            evidence_ref=evidence_ref,
            note=None,
            at="2026-09-08T01:03:00Z",
        ))

    def test_begin_is_idempotent_and_binds_clean_revision(self) -> None:
        first = self.begin()
        second = self.begin()
        self.assertEqual(first["change_id"], second["change_id"])
        self.assertFalse(first["source"]["dirty"])
        self.assertEqual(first["source"]["git_revision"],
                         first["source"]["revision_identity"])
        self.assertEqual("pending", first["evaluation"]["verdict"])
        self.assertEqual(1, len(list((self.root / "changes").glob("*.json"))))

    def test_static_change_never_claims_behavior_validation(self) -> None:
        record = self.begin(required_samples=0)
        checked = self.check(record["change_id"])
        self.assertEqual("static_validated", checked["evaluation"]["verdict"])

        failed = self.check(record["change_id"], status="failed")
        self.assertEqual("falsified", failed["evaluation"]["verdict"])
        recovered = self.check(record["change_id"],
                               evidence_ref="cmd:unit-regression-after-fix")
        self.assertEqual("static_validated",
                         recovered["evaluation"]["verdict"])

    def test_direct_reference_change_updates_source_fingerprint(self) -> None:
        reference = self.skill.parent / "references" / "behavior.md"
        reference.parent.mkdir()
        reference.write_text("old behavior\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "add behavior reference")
        arguments = argparse.Namespace(
            root=self.root,
            skill=str(self.skill),
            summary="change referenced behavior",
            acceptance=["new behavior is used"],
            artifact=[str(reference)],
            required_samples=1,
            at="2026-09-08T01:00:00Z",
        )
        first = verification.begin(arguments)
        reference.write_text("new behavior\n", encoding="utf-8")
        second = verification.begin(arguments)
        self.assertNotEqual(first["change_id"], second["change_id"])
        self.assertTrue(second["source"]["dirty"])
        self.assertEqual(2, len(second["source"]["artifacts"]))
        with self.assertRaisesRegex(ValueError, "artifact.*fingerprint"):
            self.load(first["change_id"])
        self.assertTrue(self.load(second["change_id"])["load"]["matches_change"])

    def test_behavior_requires_matching_load_and_passed_samples(self) -> None:
        record = self.begin(required_samples=2)
        checked = self.check(record["change_id"])
        self.assertEqual("pending", checked["evaluation"]["verdict"])

        loaded = self.load(record["change_id"])
        load_id = loaded["load"]["load_id"]
        first = self.sample(record["change_id"], load_id, "passed",
                            "task:sample-1")
        self.assertEqual("inconclusive", first["evaluation"]["verdict"])
        second = self.sample(record["change_id"], load_id, "passed",
                             "task:sample-2")
        self.assertEqual("validated", second["evaluation"]["verdict"])

    def test_digest_mismatch_and_failed_sample_are_rejected_or_falsified(self) -> None:
        record = self.begin(required_samples=1)
        self.check(record["change_id"])
        other = self.repo / "skills" / "other" / "SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("# Other\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.load(record["change_id"], other)

        loaded = self.load(record["change_id"])
        failed = self.sample(record["change_id"], loaded["load"]["load_id"],
                             "failed", "task:failed-s")
        self.assertEqual("falsified", failed["evaluation"]["verdict"])

    def test_cli_status_open_filters_closed_records(self) -> None:
        closed = self.begin(required_samples=0)
        self.check(closed["change_id"])
        self.skill.write_text("# Demo\n\nChanged worktree behavior.\n",
                              encoding="utf-8")
        open_record = self.begin(required_samples=1)

        command = [
            "python3", str(Path(verification.__file__)),
            "--root", str(self.root), "status", "--open",
        ]
        result = subprocess.run(command, text=True, capture_output=True,
                                check=True)
        payload = json.loads(result.stdout)
        self.assertEqual([open_record["change_id"]],
                         [item["change_id"] for item in payload["changes"]])
        self.assertEqual({"pending": 1}, payload["counts"])


if __name__ == "__main__":
    unittest.main()
