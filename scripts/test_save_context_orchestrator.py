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
    }
    values.update(overrides)
    return argparse.Namespace(**values)


COMMANDS = Commands(("audit",), ("context",))
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
            "participant_policy": "runtime-selected",
        })
        runner = RecordingRunner([
            completed(stdout="validation succeeded\n"),
            completed(stdout=audit),
            completed(stdout="wrote /context\nappended /daily: - [09:00] done\n"),
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
        self.assertEqual(["context", "audit", "context"], [call[0][0] for call in runner.calls])
        self.assertIn("--validate-only", runner.calls[0][0])
        self.assertNotIn("--validate-only", runner.calls[2][0])
        self.assertEqual("context payload", runner.calls[0][1])
        self.assertEqual("context payload", runner.calls[2][1])
        self.assertNotIn("title", receipt["stages"])

    def test_audit_failure_is_reported_without_blocking_checkpoint(self) -> None:
        runner = RecordingRunner([
            completed(stdout="validation succeeded\n"),
            completed(1, stderr="audit unavailable"),
            completed(stdout="wrote /context\ntimeline skipped\n"),
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

    def test_context_failure_is_fail_closed(self) -> None:
        runner = RecordingRunner([completed(2, stderr="invalid context")])

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
        self.assertEqual("failed", receipt["stages"]["preflight"]["status"])
        self.assertEqual("preflight_failed", receipt["stages"]["audit"]["reason"])
        self.assertEqual(1, len(runner.calls))

    def test_receipt_never_claims_native_title_write(self) -> None:
        runner = RecordingRunner([
            completed(stdout="validation succeeded\n"),
            completed(stdout="wrote /context\ntimeline already exists /daily\n"),
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
        self.assertEqual("succeeded", receipt["status"])
        self.assertEqual("skipped", receipt["stages"]["audit"]["status"])
        self.assertEqual(["context", "context"], [call[0][0] for call in runner.calls])
        self.assertNotIn("title", receipt["stages"])

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
            {"preflight", "audit", "context"},
            {
                name
                for name, stage in receipt["stages"].items()
                if stage.get("reason") == "continue_work"
            },
        )

    def test_explicit_pause_override_allows_checkpoint(self) -> None:
        runner = RecordingRunner([
            completed(stdout="validation succeeded\n"),
            completed(stdout="wrote /context\ntimeline skipped\n"),
        ])

        code, receipt = orchestrate(
            arguments(
                audit_thread_id=None,
                audit_cwd=None,
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
        self.assertEqual(["context", "context"], [call[0][0] for call in runner.calls])

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

    def test_real_entry_requires_compiler_owned_next_route_for_mainline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            admission_path = Path(tmp) / "admission.json"
            context_path = Path(tmp) / "context.md"
            admission_path.write_text(
                json.dumps(READY_ADMISSION), encoding="utf-8"
            )
            context_path.write_text("not read before route gate", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--orchestrate",
                    "--admission-file", str(admission_path),
                    "amt",
                    "--context-file", str(context_path),
                    "--skip-timeline",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn(
                "orchestrated mainline save requires --next-route",
                result.stderr,
            )

    def test_real_entry_rejects_invalid_context_before_audit_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            admission_path = Path(tmp) / "admission.json"
            context_path = Path(tmp) / "context.md"
            admission_path.write_text(
                json.dumps(READY_ADMISSION), encoding="utf-8"
            )
            context_path.write_text("invalid context", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--orchestrate",
                    "--admission-file", str(admission_path),
                    "--audit-thread-id", "thread-that-must-not-dispatch",
                    "--audit-cwd", "/project",
                    "amt",
                    "--context-file", str(context_path),
                    "--next-route", "none",
                    "--skip-timeline",
                ],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(2, result.returncode)
            receipt = json.loads(result.stdout)
            self.assertEqual("failed", receipt["stages"]["preflight"]["status"])
            self.assertEqual(
                "preflight_failed", receipt["stages"]["audit"]["reason"]
            )
            self.assertFalse((Path(tmp) / ".ai" / "audits").exists())


if __name__ == "__main__":
    unittest.main()
