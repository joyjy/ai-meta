#!/usr/bin/env python3
"""Regression tests for asynchronous Rollerskate audit dispatch."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from save_context_audit_rs import (  # noqa: E402
    parse_audit_candidates,
    read_audit_summary,
)


SCRIPT = Path(__file__).with_name("save_context_audit_rs.py")


class SaveContextAuditRsTest(unittest.TestCase):

    def test_summary_candidate_ids_are_derived_from_valid_yaml_lane_order(self) -> None:
        candidates = parse_audit_candidates(
            "schema: agent.audit.v1\n"
            "execution_friction:\n"
            "- audit_id: friction-a\n"
            "  evidence:\n"
            "  - 'audit_id: not-a-candidate'\n"
            "prompt_contract_gaps:\n"
            "  - audit_id: prompt-b\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            summary_path = Path(tmp) / "audit-summary.json"
            summary_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-summary.v1",
                    "thread_id": "thread-audit",
                    "object": "save-context audit",
                    "finding": "Two evidence-backed findings exist.",
                    "evidence": ["agent-audit.yaml"],
                    "recommendation": "Review both candidates.",
                    "candidate_ids": ["worker-guessed-id"],
                }),
                encoding="utf-8",
            )

            summary = read_audit_summary(
                summary_path, "thread-audit", candidates
            )

        self.assertEqual(
            ["friction-a", "prompt-b"], summary["candidate_ids"]
        )

    def test_audit_candidates_reject_duplicate_lane_keys(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "duplicate key"):
            parse_audit_candidates(
                "schema: agent.audit.v1\n"
                "execution_friction: []\n"
                "execution_friction: []\n"
                "prompt_contract_gaps: []\n"
            )

    def test_dispatches_once_to_kimi_without_waiting_for_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / "codex"
            rollout = (
                codex_home / "sessions/2026/08/07"
                / "rollout-2026-08-07T01-02-03-thread-audit.jsonl"
            )
            rollout.parent.mkdir(parents=True)
            rollout.write_text(
                json.dumps({
                    "timestamp": "2026-08-07T01:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "session_id": "thread-audit",
                        "cwd": "/workspace/project",
                        "originator": "Codex Desktop",
                    },
                }) + "\n" + json.dumps({
                    "timestamp": "2026-08-07T01:01:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "save context"}],
                    },
                }) + "\n",
                encoding="utf-8",
            )
            fake_rs = root / "rs"
            capture = root / "captured-run.json"
            counter = root / "calls.txt"
            fake_rs.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "if sys.argv[1:3] == ['run', 'start'] and len(sys.argv) == 4:\n"
                "    payload = json.loads(pathlib.Path(sys.argv[3]).read_text())\n"
                "    pathlib.Path(os.environ['FAKE_CAPTURE']).write_text(json.dumps(payload))\n"
                "    counter = pathlib.Path(os.environ['FAKE_COUNTER'])\n"
                "    counter.write_text(counter.read_text() + 'x' if counter.exists() else 'x')\n"
                "    print(json.dumps({'status': 'accepted', 'run': {'runId': 'run_test'}}))\n"
                "elif sys.argv[1:3] == ['run', 'inspect']:\n"
                "    print(json.dumps({'summary': {\n"
                "        'status': 'active',\n"
                "        'terminalSummary': 'still running',\n"
                "    }}))\n"
                "else:\n"
                "    raise SystemExit(2)\n",
                encoding="utf-8",
            )
            fake_rs.chmod(0o755)
            audit_root = root / "audits"
            environment = {
                **os.environ,
                "FAKE_CAPTURE": str(capture),
                "FAKE_COUNTER": str(counter),
            }
            command = [
                sys.executable,
                str(SCRIPT),
                "dispatch",
                "--thread-id", "thread-audit",
                "--codex-home", str(codex_home),
                "--cwd", "/workspace/project",
                "--route", "amt:mainline",
                "--audit-root", str(audit_root),
                "--rs-command", str(fake_rs),
            ]

            first = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            second = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            receipt = json.loads(first.stdout)
            self.assertEqual(receipt, json.loads(second.stdout))
            self.assertEqual("pending", receipt["status"])
            self.assertEqual("run_test", receipt["run_id"])
            self.assertEqual("kimi", receipt["steward"])
            self.assertEqual("x", counter.read_text(encoding="utf-8"))
            self.assertFalse(Path(receipt["output_path"]).exists())

            run_request = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual("RunIntent@1", run_request["schemaVersion"])
            self.assertEqual(
                f"save-context-audit-{receipt['audit_id']}",
                run_request["requestId"],
            )
            self.assertEqual("change", run_request["desiredEffect"])
            self.assertEqual(
                ["agent:kimi"],
                run_request["requestedParticipantRefs"],
            )
            self.assertEqual(
                Path(receipt["workspace"]).as_uri(),
                run_request["workspaceRef"],
            )
            self.assertEqual(
                [
                    Path(receipt["output_path"]).as_uri(),
                    Path(receipt["summary_path"]).as_uri(),
                ],
                run_request["terminalEvidence"],
            )
            self.assertNotIn("steward", run_request)
            self.assertNotIn("workspace", run_request)
            self.assertNotIn("maxSteps", run_request)
            self.assertNotIn("maxDepth", run_request)
            workspace = Path(receipt["workspace"])
            self.assertTrue((workspace / "AUDITOR.md").is_file())
            self.assertTrue((workspace / "recovery-packet.md").is_file())
            self.assertFalse((workspace / "rollout.jsonl").exists())
            self.assertIn(
                "plain-language `save-context.audit-summary.v1` JSON",
                (workspace / "AUDIT_TASK.md").read_text(encoding="utf-8"),
            )

            status = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "status",
                    "--receipt", receipt["receipt_path"],
                    "--rs-command", str(fake_rs),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, status.returncode, status.stderr)
            status_payload = json.loads(status.stdout)
            self.assertEqual("active", status_payload["status"])
            self.assertEqual("still running", status_payload["terminal_summary"])
            self.assertFalse(status_payload["cleanup_ready"])

            Path(receipt["output_path"]).write_text(
                "schema: agent.audit.v1\n"
                "thread_id: thread-audit\n"
                "execution_friction: []\n"
                "prompt_contract_gaps: []\n",
                encoding="utf-8",
            )
            Path(receipt["summary_path"]).write_text(
                json.dumps({
                    "schema": "save-context.audit-summary.v1",
                    "thread_id": "thread-audit",
                    "object": "save-context audit",
                    "finding": "No evidence-backed finding exists.",
                    "evidence": [],
                    "recommendation": "No action.",
                    "candidate_ids": ["worker-guessed-id"],
                }),
                encoding="utf-8",
            )
            ready = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "status",
                    "--receipt", receipt["receipt_path"],
                    "--rs-command", str(fake_rs),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, ready.returncode, ready.stderr)
            ready_payload = json.loads(ready.stdout)
            self.assertEqual("ready", ready_payload["status"])
            self.assertTrue(ready_payload["needs_settlement"])
            self.assertFalse(ready_payload["cleanup_ready"])
            self.assertEqual(
                {"execution_friction": 0, "prompt_contract_gaps": 0},
                ready_payload["candidate_counts"],
            )
            self.assertEqual(
                "No evidence-backed finding exists.",
                ready_payload["audit_summary"]["finding"],
            )
            self.assertEqual([], ready_payload["audit_summary"]["candidate_ids"])

            settlement_input = root / "settlement-input.json"
            settlement_input.write_text(
                json.dumps({
                    "schema": "save-context.audit-settlement.v1",
                    "items": [],
                }),
                encoding="utf-8",
            )
            settled = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "settle",
                    "--receipt", receipt["receipt_path"],
                    "--input", str(settlement_input),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, settled.returncode, settled.stderr)
            settled_payload = json.loads(settled.stdout)
            self.assertEqual("settled", settled_payload["status"])
            self.assertTrue(settled_payload["cleanup_ready"])

            settled_status = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "status",
                    "--receipt", receipt["receipt_path"],
                    "--rs-command", str(fake_rs),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, settled_status.returncode, settled_status.stderr)
            self.assertEqual("settled", json.loads(settled_status.stdout)["status"])

    def test_redispatches_legacy_receipt_through_current_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / "codex"
            rollout = (
                codex_home / "sessions/2026/08/14"
                / "rollout-2026-08-14T01-02-03-thread-legacy.jsonl"
            )
            rollout.parent.mkdir(parents=True)
            rollout.write_text(
                json.dumps({
                    "timestamp": "2026-08-14T01:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "session_id": "thread-legacy",
                        "cwd": "/workspace/project",
                        "originator": "Codex Desktop",
                    },
                }) + "\n" + json.dumps({
                    "timestamp": "2026-08-14T01:01:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "save context"}],
                    },
                }) + "\n",
                encoding="utf-8",
            )
            audit_root = root / "audits"
            legacy_dir = audit_root / "legacy-audit"
            legacy_workspace = legacy_dir / "workspace"
            legacy_workspace.mkdir(parents=True)
            (legacy_workspace / "AUDIT_TASK.md").write_text(
                "# Save-context audit task\n\n"
                "- project_cwd: `/workspace/project`\n",
                encoding="utf-8",
            )
            (legacy_workspace / "recovery-packet.md").write_text(
                "# Recovery packet\n\n- session_id: `thread-legacy`\n",
                encoding="utf-8",
            )
            legacy_receipt_path = legacy_dir / "receipt.json"
            legacy_receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "legacy-audit",
                    "status": "pending",
                    "run_id": "run_legacy",
                    "steward": "kimi",
                    "thread_id": "thread-legacy",
                    "route": "amt:mainline",
                    "rollout": str(rollout),
                    "ll_path": None,
                    "workspace": str(legacy_workspace),
                    "output_path": str(legacy_workspace / "agent-audit.yaml"),
                    "receipt_path": str(legacy_receipt_path),
                }),
                encoding="utf-8",
            )
            fake_rs = root / "rs"
            capture = root / "captured-run.json"
            fake_rs.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "if sys.argv[1:3] == ['run', 'start'] and len(sys.argv) == 4:\n"
                "    payload = json.loads(pathlib.Path(sys.argv[3]).read_text())\n"
                "    pathlib.Path(os.environ['FAKE_CAPTURE']).write_text(json.dumps(payload))\n"
                "    print(json.dumps({'status': 'accepted', 'run': {'runId': 'run_new'}}))\n"
                "elif sys.argv[1:3] == ['run', 'inspect']:\n"
                "    print(json.dumps({'summary': {'status': 'active'}}))\n"
                "else:\n"
                "    raise SystemExit(2)\n",
                encoding="utf-8",
            )
            fake_rs.chmod(0o755)
            environment = {**os.environ, "FAKE_CAPTURE": str(capture)}
            rollout.unlink()

            redispatched = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "redispatch",
                    "--receipt", str(legacy_receipt_path),
                    "--rs-command", str(fake_rs),
                    "--codex-home", str(codex_home),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, redispatched.returncode, redispatched.stderr)
            successor = json.loads(redispatched.stdout)
            self.assertNotEqual("legacy-audit", successor["audit_id"])
            self.assertEqual(
                "run-intent-owner-compiled-v3-derived-summary-ids",
                successor["dispatch_contract"],
            )
            self.assertEqual("/workspace/project", successor["project_cwd"])
            self.assertEqual(
                {
                    "audit_id": "legacy-audit",
                    "receipt": str(legacy_receipt_path.resolve()),
                },
                successor["supersedes"],
            )
            run_request = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual("RunIntent@1", run_request["schemaVersion"])
            self.assertNotIn("workspace", run_request)
            self.assertNotIn("maxSteps", run_request)

            successor_output = Path(successor["output_path"])
            successor_output.write_text(
                "schema: agent.audit.v1\n"
                "thread_id: thread-legacy\n"
                "execution_friction: []\n"
                "prompt_contract_gaps: []\n",
                encoding="utf-8",
            )
            Path(successor["summary_path"]).write_text(
                json.dumps({
                    "schema": "save-context.audit-summary.v1",
                    "thread_id": "thread-legacy",
                    "object": "legacy audit",
                    "finding": "No evidence-backed finding exists.",
                    "evidence": [],
                    "recommendation": "No action.",
                    "candidate_ids": [],
                }),
                encoding="utf-8",
            )
            superseded = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "supersede",
                    "--receipt", str(legacy_receipt_path),
                    "--successor-receipt", successor["receipt_path"],
                    "--reason", "Replaced by current RunIntent contract",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, superseded.returncode, superseded.stderr)
            superseded_payload = json.loads(superseded.stdout)
            self.assertEqual("superseded", superseded_payload["status"])
            self.assertEqual(successor["audit_id"], superseded_payload["successor_audit_id"])

            old_status = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "status",
                    "--receipt", str(legacy_receipt_path),
                    "--rs-command", str(fake_rs),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, old_status.returncode, old_status.stderr)
            old_status_payload = json.loads(old_status.stdout)
            self.assertEqual("superseded", old_status_payload["status"])
            self.assertEqual(
                successor["audit_id"], old_status_payload["successor_audit_id"]
            )
            self.assertEqual(
                successor["receipt_path"], old_status_payload["successor_receipt"]
            )

            pruned = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "prune",
                    "--receipt", str(legacy_receipt_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, pruned.returncode, pruned.stderr)
            pruned_payload = json.loads(pruned.stdout)
            self.assertEqual("cleanup-ready", pruned_payload["status"])
            self.assertTrue(pruned_payload["dry_run"])
            self.assertEqual(
                [str(legacy_workspace.resolve())], pruned_payload["paths"]
            )
            self.assertTrue(legacy_workspace.is_dir())

    def test_settlement_must_account_for_every_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "audit"
            workspace = audit_dir / "workspace"
            workspace.mkdir(parents=True)
            output_path = workspace / "agent-audit.yaml"
            output_path.write_text(
                "schema: agent.audit.v1\n"
                "thread_id: thread-audit\n"
                "execution_friction:\n"
                "- audit_id: friction-a\n"
                "prompt_contract_gaps: []\n",
                encoding="utf-8",
            )
            receipt_path = audit_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "audit",
                    "status": "pending",
                    "run_id": "run_test",
                    "workspace": str(workspace),
                    "output_path": str(output_path),
                }),
                encoding="utf-8",
            )
            settlement_input = root / "settlement-input.json"
            settlement_input.write_text(
                json.dumps({
                    "schema": "save-context.audit-settlement.v1",
                    "items": [],
                }),
                encoding="utf-8",
            )
            template = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "settle",
                    "--receipt", str(receipt_path),
                    "--template",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, template.returncode, template.stderr)
            self.assertEqual(
                [{
                    "lane": "execution_friction",
                    "audit_id": "friction-a",
                    "disposition": "",
                    "destination": "",
                    "reason": "",
                    "durable_ref": "",
                }],
                json.loads(template.stdout)["items"],
            )
            self.assertFalse((audit_dir / "settlement.json").exists())
            settled = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "settle",
                    "--receipt", str(receipt_path),
                    "--input", str(settlement_input),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, settled.returncode)
            self.assertIn("missing candidates", settled.stderr)

    def test_discard_then_prune_preserves_tombstone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "audit"
            workspace = audit_dir / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "recovery-packet.md").write_text("packet", encoding="utf-8")
            (audit_dir / "run.json").write_text("{}", encoding="utf-8")
            receipt_path = audit_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "audit",
                    "status": "pending",
                    "run_id": "run_test",
                    "workspace": str(workspace),
                    "output_path": str(workspace / "agent-audit.yaml"),
                }),
                encoding="utf-8",
            )
            (audit_dir / "inspection.json").write_text(
                json.dumps({
                    "schema": "save-context.audit-inspection.v1",
                    "run_id": "run_test",
                    "status": "failed",
                    "terminal_summary": "no valid output",
                }),
                encoding="utf-8",
            )
            discarded = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "discard",
                    "--receipt", str(receipt_path),
                    "--reason", "terminal run has no valid output",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, discarded.returncode, discarded.stderr)
            self.assertEqual("discarded", json.loads(discarded.stdout)["status"])

            dry_run = subprocess.run(
                [sys.executable, str(SCRIPT), "prune", "--receipt", str(receipt_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stderr)
            self.assertTrue(json.loads(dry_run.stdout)["dry_run"])
            self.assertTrue(workspace.exists())

            pruned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prune",
                    "--receipt", str(receipt_path),
                    "--yes",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, pruned.returncode, pruned.stderr)
            pruned_payload = json.loads(pruned.stdout)
            self.assertFalse(workspace.exists())
            self.assertFalse((audit_dir / "run.json").exists())
            self.assertTrue(receipt_path.exists())
            self.assertTrue((audit_dir / "settlement.json").exists())
            archive_path = Path(pruned_payload["archive_path"])
            digest_path = Path(pruned_payload["archive_digest_path"])
            self.assertTrue(archive_path.is_file())
            self.assertTrue(digest_path.is_file())
            self.assertEqual(64, len(pruned_payload["archive_sha256"]))

            repeated = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prune",
                    "--receipt", str(receipt_path),
                    "--yes",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, repeated.returncode, repeated.stderr)
            self.assertEqual(
                pruned_payload["archive_sha256"],
                json.loads(repeated.stdout)["archive_sha256"],
            )

    def test_prune_keeps_sources_when_compression_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "audit"
            workspace = audit_dir / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "recovery-packet.md").write_text("packet", encoding="utf-8")
            (audit_dir / "run.json").write_text("{}", encoding="utf-8")
            receipt_path = audit_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "audit",
                    "status": "pending",
                    "run_id": "run_test",
                    "workspace": str(workspace),
                    "output_path": str(workspace / "agent-audit.yaml"),
                }),
                encoding="utf-8",
            )
            (audit_dir / "settlement.json").write_text(
                json.dumps({
                    "schema": "save-context.audit-settlement.v1",
                    "audit_id": "audit",
                    "status": "discarded",
                    "terminal_status": "failed",
                    "settled_at": "2026-08-24T00:00:00+00:00",
                    "candidate_counts": {},
                    "items": [],
                    "reason": "test",
                }),
                encoding="utf-8",
            )
            failing_zstd = root / "failing-zstd"
            failing_zstd.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
            failing_zstd.chmod(0o755)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prune",
                    "--receipt", str(receipt_path),
                    "--yes",
                    "--zstd-command", str(failing_zstd),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertTrue(workspace.is_dir())
            self.assertTrue((audit_dir / "run.json").is_file())
            self.assertFalse((root / "archived/2026-08/audit.tar.zst").exists())

    def test_inventory_reports_exact_paths_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_root = root / "audits"
            audit_dir = audit_root / "audit-ready"
            workspace = audit_dir / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "agent-audit.yaml").write_text("schema: agent.audit.v1\n", encoding="utf-8")
            (audit_dir / "run.json").write_text("{}", encoding="utf-8")
            receipt_path = audit_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "audit-ready",
                    "status": "pending",
                    "run_id": "run_archived",
                    "workspace": str(workspace),
                    "output_path": str(workspace / "agent-audit.yaml"),
                }),
                encoding="utf-8",
            )
            (audit_dir / "settlement.json").write_text(
                json.dumps({
                    "schema": "save-context.audit-settlement.v1",
                    "audit_id": "audit-ready",
                    "status": "settled",
                    "settled_at": "2026-08-24T00:00:00+00:00",
                    "candidate_counts": {
                        "execution_friction": 0,
                        "prompt_contract_gaps": 0,
                    },
                    "items": [],
                }),
                encoding="utf-8",
            )
            incomplete = audit_root / "audit-incomplete"
            incomplete.mkdir()
            runtime_db = root / "runtime.db"
            connection = sqlite3.connect(runtime_db)
            connection.execute(
                "CREATE TABLE agent_runs (run_id TEXT PRIMARY KEY, archived_at TEXT)"
            )
            connection.execute(
                "INSERT INTO agent_runs VALUES (?, ?)",
                ("run_archived", "2026-08-24T01:00:00Z"),
            )
            connection.commit()
            connection.close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inventory",
                    "--audit-root", str(audit_root),
                    "--runtime-db", str(runtime_db),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(2, payload["count"])
            ready = next(item for item in payload["audits"] if item["audit_id"] == "audit-ready")
            self.assertTrue(ready["eligible"])
            self.assertEqual("archived", ready["run_archive_status"])
            self.assertEqual(
                [str(workspace.resolve()), str((audit_dir / "run.json").resolve())],
                ready["cleanup_paths"],
            )
            blocked = next(item for item in payload["audits"] if item["audit_id"] == "audit-incomplete")
            self.assertFalse(blocked["eligible"])
            self.assertEqual(["missing_receipt"], blocked["exclusion_reasons"])
            self.assertTrue(workspace.is_dir())
            self.assertTrue((audit_dir / "run.json").is_file())

    def test_inventory_reports_runtime_database_schema_errors_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_db = root / "runtime.db"
            sqlite3.connect(runtime_db).close()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inventory",
                    "--audit-root", str(root / "audits"),
                    "--runtime-db", str(runtime_db),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("cannot read Rollerskate runtime database", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_prune_rejects_workspace_outside_audit_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "audit"
            outside = root / "outside"
            audit_dir.mkdir()
            outside.mkdir()
            (outside / "keep.txt").write_text("keep", encoding="utf-8")
            receipt_path = audit_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps({
                    "schema": "save-context.audit-dispatch.v1",
                    "audit_id": "audit",
                    "status": "pending",
                    "run_id": "run_test",
                    "workspace": str(outside),
                    "output_path": str(outside / "agent-audit.yaml"),
                }),
                encoding="utf-8",
            )
            (audit_dir / "settlement.json").write_text(
                json.dumps({
                    "schema": "save-context.audit-settlement.v1",
                    "audit_id": "audit",
                    "status": "discarded",
                    "candidate_counts": {},
                    "items": [],
                }),
                encoding="utf-8",
            )
            pruned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "prune",
                    "--receipt", str(receipt_path),
                    "--yes",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, pruned.returncode)
            self.assertIn("escapes audit directory", pruned.stderr)
            self.assertTrue((outside / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
