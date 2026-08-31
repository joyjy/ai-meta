#!/usr/bin/env python3
"""Workflow tests for the save-context checkpoint orchestrator."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from save_context_orchestrator import (  # noqa: E402
    Commands,
    orchestrate,
    parse_admission,
)


class RecordingRunner:
    def __init__(self, results: list[subprocess.CompletedProcess[str]]) -> None:
        self.results = results
        self.calls: list[tuple[list[str], str | None]] = []

    def __call__(
        self, command: list[str], input_text: str | None
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, input_text))
        return self.results.pop(0)


def completed(code: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def arguments(**overrides: object) -> argparse.Namespace:
    values = {
        "abbr": "amt:work",
        "audit_thread_id": "thread-1",
        "audit_rollout": None,
        "audit_cwd": "/project",
        "audit_ll": None,
        "pause_override": False,
        "refresh_title": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


COMMANDS = Commands(("audit",), ("context",), ("title",))
SCRIPT = Path(__file__).with_name("save_context_orchestrator.py")
READY_ADMISSION = {
    "schema": "save-context.admission.v1",
    "decision": "checkpoint_ready",
    "checked": ["task:no-actionable-work"],
    "actionable": [],
}
CONTINUE_ADMISSION = {
    "schema": "save-context.admission.v1",
    "decision": "continue_work",
    "checked": ["gitlab:pipeline:792714=failed"],
    "actionable": ["diagnose pipeline 792714 before checkpoint"],
}


class OrchestratorWorkflowTest(unittest.TestCase):
    def test_success_runs_fixed_order_and_returns_compact_receipt(self) -> None:
        audit = json.dumps({
            "status": "pending",
            "run_id": "run-1",
            "receipt_path": "/audit/receipt.json",
            "output_path": "/audit/agent-audit.yaml",
            "steward": "kimi",
        })
        runner = RecordingRunner([
            completed(stdout=audit),
            completed(stdout="wrote /context\nappended /daily: - [09:00] done\n"),
            completed(stdout="Codex session titles refreshed: db=1\n"),
        ])

        code, receipt = orchestrate(
            arguments(),
            ["amt:work", "--context-stdin", "--timeline", "[09:00] done"],
            "context payload",
            READY_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(0, code)
        self.assertEqual("succeeded", receipt["status"])
        self.assertEqual(["audit", "context", "title"], [call[0][0] for call in runner.calls])
        self.assertEqual("context payload", runner.calls[1][1])
        self.assertEqual(
            ["title", "--current", "--daily-note-title", "[09:00] done"],
            runner.calls[2][0],
        )

    def test_audit_failure_is_reported_without_blocking_checkpoint(self) -> None:
        runner = RecordingRunner([
            completed(1, stderr="audit unavailable"),
            completed(stdout="wrote /context\ntimeline skipped\n"),
            completed(stdout="Codex state not found; skipped\n"),
        ])

        code, receipt = orchestrate(
            arguments(),
            ["amt:work", "--context-file", "/tmp/context", "--skip-timeline"],
            None,
            READY_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(0, code)
        self.assertEqual("degraded", receipt["status"])
        self.assertEqual("failed", receipt["stages"]["audit"]["status"])
        self.assertEqual("succeeded", receipt["stages"]["context"]["status"])
        self.assertEqual(3, len(runner.calls))

    def test_context_failure_is_fail_closed_and_skips_title(self) -> None:
        runner = RecordingRunner([
            completed(stdout=json.dumps({"status": "pending", "run_id": "run-1"})),
            completed(2, stderr="invalid context"),
        ])

        code, receipt = orchestrate(
            arguments(),
            ["amt:work", "--context-stdin", "--skip-timeline"],
            "malformed",
            READY_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(2, code)
        self.assertEqual("failed", receipt["status"])
        self.assertEqual("context_failed", receipt["stages"]["title"]["reason"])
        self.assertEqual(2, len(runner.calls))

    def test_title_failure_is_non_blocking_and_timeline_duplicate_is_not_reused(self) -> None:
        runner = RecordingRunner([
            completed(stdout="wrote /context\ntimeline already exists /daily\n"),
            completed(1, stderr="title database is locked"),
        ])

        code, receipt = orchestrate(
            arguments(audit_thread_id=None, audit_cwd=None),
            ["amt:work", "--context-file", "/tmp/context", "--timeline", "done"],
            None,
            READY_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(0, code)
        self.assertEqual("degraded", receipt["status"])
        self.assertEqual("skipped", receipt["stages"]["audit"]["status"])
        self.assertEqual(["title", "--current"], runner.calls[1][0])
        self.assertEqual("failed", receipt["stages"]["title"]["status"])

    def test_continue_work_skips_every_output_stage(self) -> None:
        runner = RecordingRunner([])

        code, receipt = orchestrate(
            arguments(),
            ["amt:work", "--context-file", "/tmp/context"],
            None,
            CONTINUE_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(3, code)
        self.assertEqual("continue_work", receipt["status"])
        self.assertEqual("blocked", receipt["stages"]["admission"]["status"])
        self.assertEqual([], runner.calls)
        self.assertEqual(
            {"audit", "context", "title"},
            {
                name
                for name, stage in receipt["stages"].items()
                if stage.get("reason") == "continue_work"
            },
        )

    def test_explicit_pause_override_allows_checkpoint(self) -> None:
        runner = RecordingRunner([
            completed(stdout="wrote /context\ntimeline skipped\n"),
        ])

        code, receipt = orchestrate(
            arguments(
                audit_thread_id=None,
                audit_cwd=None,
                refresh_title=False,
                pause_override=True,
            ),
            ["amt:work", "--context-file", "/tmp/context", "--skip-timeline"],
            None,
            CONTINUE_ADMISSION,
            COMMANDS,
            runner,
        )

        self.assertEqual(0, code)
        self.assertEqual("succeeded", receipt["status"])
        self.assertEqual("overridden", receipt["stages"]["admission"]["status"])
        self.assertEqual(["context"], [call[0][0] for call in runner.calls])

    def test_admission_rejects_inconsistent_decision(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot contain actionable"):
            parse_admission(json.dumps({
                **READY_ADMISSION,
                "actionable": ["pipeline failed"],
            }))

    def test_admission_rejects_unbounded_items(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty string list"):
            parse_admission(json.dumps({
                **READY_ADMISSION,
                "checked": ["x" * 501],
            }))

    def test_real_entry_keeps_repeated_timeline_checkpoint_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            admission_path = Path(tmp) / "admission.json"
            admission_path.write_text(
                json.dumps(READY_ADMISSION), encoding="utf-8"
            )
            command = [
                sys.executable,
                str(SCRIPT),
                "--orchestrate",
                "--admission-file",
                str(admission_path),
                "amt",
                "--timeline-only",
                "--timeline",
                "[09:00-09:10] orchestrator smoke",
            ]

            first = subprocess.run(
                command, text=True, capture_output=True, check=False, env=env
            )
            second = subprocess.run(
                command, text=True, capture_output=True, check=False, env=env
            )

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual("appended", json.loads(first.stdout)["stages"]["context"]["timeline"])
            self.assertEqual("unchanged", json.loads(second.stdout)["stages"]["context"]["timeline"])
            daily_notes = list(
                (Path(tmp) / "Documents" / "me" / "Daily Notes").glob("*/*.md")
            )
            self.assertEqual(1, len(daily_notes))
            self.assertEqual(
                1,
                daily_notes[0].read_text(encoding="utf-8").count("orchestrator smoke"),
            )


if __name__ == "__main__":
    unittest.main()
