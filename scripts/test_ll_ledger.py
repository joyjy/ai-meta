from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

LEDGER = Path(__file__).with_name("ll-ledger")
VERIFIER = Path(__file__).with_name("verify-ll-contract")
FIXTURE = (Path(__file__).with_name("fixtures") / "ll-contracts" /
           "engineering_exit_codex_goal.json")


class LLLedgerTest(unittest.TestCase):

    def test_init_refuses_to_overwrite_an_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            ledger = root / "session.ll"
            source.write_text(FIXTURE.read_text(encoding="utf-8"),
                              encoding="utf-8")
            ledger.write_text("keep-existing-history\n", encoding="utf-8")

            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(1, initialized.returncode)
            self.assertIn("refusing to overwrite", initialized.stderr)
            self.assertEqual("keep-existing-history\n",
                             ledger.read_text(encoding="utf-8"))

    def test_single_file_keeps_fixed_front_and_appends_effective_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            ledger = root / "session.ll"
            source.write_text(FIXTURE.read_text(encoding="utf-8"),
                              encoding="utf-8")

            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            before = ledger.read_text(encoding="utf-8").splitlines()[:8]
            self.assertEqual(8, len(before))

            event = root / "event.json"
            event.write_text(json.dumps({
                "type": "exit",
                "state": "needs_human",
                "next_action": "manual",
            }), encoding="utf-8")
            appended = subprocess.run(
                [str(LEDGER), "append", str(ledger), "--event-file", str(event)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, appended.returncode, appended.stderr)
            after = ledger.read_text(encoding="utf-8").splitlines()[:8]
            self.assertEqual(before, after)

            verified = subprocess.run(
                [str(VERIFIER), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, verified.returncode, verified.stdout)
            tailed = subprocess.run(
                [str(LEDGER), "tail", str(ledger), "--count", "1"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertIn('"type":"exit"', tailed.stdout)
            self.assertIn('"state":"needs_human"', tailed.stdout)

    def test_archive_verifies_and_moves_exact_ledger_without_globs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            ledger = root / "session.ll"
            source.write_text(FIXTURE.read_text(encoding="utf-8"),
                              encoding="utf-8")
            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)

            archived = subprocess.run(
                [str(LEDGER), "archive", str(ledger), "--destination",
                 "completed"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, archived.returncode, archived.stderr)
            payload = json.loads(archived.stdout)
            self.assertEqual("completed", payload["destination"])
            self.assertIsNone(payload["sidecar"])
            self.assertFalse(ledger.exists())
            self.assertTrue((root / "completed" / "session.ll").is_file())

    def test_archive_refuses_invalid_ledger_before_moving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "broken.ll"
            ledger.write_text("not a ledger\n", encoding="utf-8")

            archived = subprocess.run(
                [str(LEDGER), "archive", str(ledger), "--destination",
                 "review"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(1, archived.returncode)
            self.assertIn("verification failed", archived.stderr)
            self.assertTrue(ledger.is_file())
            self.assertFalse((root / "review").exists())

    def test_append_keeps_current_task_correction_in_the_ll_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            ledger = root / "session.ll"
            source.write_text(FIXTURE.read_text(encoding="utf-8"),
                              encoding="utf-8")
            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            event = root / "event.json"
            event.write_text(json.dumps({
                "type": "feedback",
                "item": {
                    "id": "current-correction",
                    "source": "user",
                    "quote": "acceptance must include smoke verification",
                    "type": "current_task_correction",
                    "problem": "active acceptance is incomplete",
                    "disposition": "applied_to_contract",
                    "current_task_impact": "updates_acceptance",
                },
            }), encoding="utf-8")

            appended = subprocess.run(
                [str(LEDGER), "append", str(ledger), "--event-file", str(event)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, appended.returncode, appended.stderr)
            self.assertIn("appended feedback event", appended.stdout)
            self.assertIn('"type":"current_task_correction"',
                          ledger.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
