#!/usr/bin/env python3
"""Regression tests for agent_frictions.py."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("agent_frictions.py")
SPEC = importlib.util.spec_from_file_location("agent_frictions", MODULE_PATH)
assert SPEC and SPEC.loader
agent_frictions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent_frictions)


class AgentFrictionsTest(unittest.TestCase):

    def setUp(self) -> None:
        self.now = datetime(2026, 7, 13, 8, 0, tzinfo=timezone.utc)

    def write_rollout(self, root: Path) -> Path:
        rollout = root / "rollout-thread-1.jsonl"
        events = [
            {
                "timestamp": "2026-07-13T01:00:00Z",
                "type": "session_meta",
                "payload": {
                    "session_id": "thread-1",
                    "cwd": "/repo",
                },
            },
            {
                "timestamp": "2026-07-13T01:01:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "turn_aborted",
                    "turn_id": "turn-abort",
                    "reason": "interrupted",
                    "duration_ms": 1000,
                },
            },
            {
                "timestamp": "2026-07-13T01:02:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "patch_apply_end",
                    "turn_id": "turn-1",
                    "call_id": "call-1",
                    "success": True,
                    "changes": {
                        "/repo/a.md": {
                            "kind": "update"
                        }
                    },
                },
            },
            {
                "timestamp": "2026-07-13T01:03:00Z",
                "type": "response_item",
                "payload": {
                    "type":
                        "message",
                    "role":
                        "user",
                    "content": [{
                        "type": "input_text",
                        "text": "SECRET-PROMPT"
                    }],
                },
            },
            {
                "timestamp": "2026-07-13T01:04:00Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "output": [{
                        "type": "text",
                        "text": "SECRET-TOOL-OUTPUT"
                    }],
                },
            },
            {
                "timestamp": "2026-07-13T01:05:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "patch_apply_end",
                    "turn_id": "turn-2",
                    "call_id": "call-2",
                    "success": True,
                    "changes": {
                        "/repo/a.md": {
                            "kind": "update"
                        }
                    },
                },
            },
            {
                "timestamp": "2026-07-13T01:06:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "patch_apply_end",
                    "turn_id": "turn-3",
                    "call_id": "call-fail",
                    "success": False,
                    "changes": {
                        "/repo/b.md": {
                            "kind": "update"
                        }
                    },
                },
            },
            {
                "timestamp": "2026-07-13T01:07:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "patch_apply_end",
                    "turn_id": "turn-4",
                    "call_id": "call-3",
                    "success": True,
                    "changes": {
                        "/repo/a.md": {
                            "kind": "update"
                        }
                    },
                },
            },
            {
                "timestamp": "2026-07-13T01:08:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "patch_apply_end",
                    "turn_id": "turn-5",
                    "call_id": "call-4",
                    "success": True,
                    "changes": {
                        "/repo/a.md": {
                            "kind": "update"
                        }
                    },
                },
            },
        ]
        rollout.write_text("".join(
            json.dumps(event) + "\n" for event in events),
                           encoding="utf-8")
        return rollout

    def all_events(self, root: Path) -> list[dict]:
        return [
            agent_frictions.read_event(path)
            for path in agent_frictions.iter_event_paths(root)
        ]

    def test_collect_is_idempotent_and_does_not_copy_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)

            first = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                   self.now)
            second = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                    self.now)

            self.assertEqual(3, len(first["created_event_ids"]))
            self.assertEqual([], second["created_event_ids"])
            self.assertEqual(first["created_event_ids"],
                             second["existing_event_ids"])
            events = self.all_events(store)
            self.assertEqual(
                {
                    "task_aborted", "patch_failure",
                    "repeated_file_edit_candidate"
                }, {event["event_type"] for event in events})
            repeated = next(
                event for event in events
                if event["event_type"] == "repeated_file_edit_candidate")
            self.assertEqual("a.md", repeated["facts"]["path"])
            self.assertEqual(4, repeated["facts"]["distinct_turn_count"])
            persisted = "\n".join(
                path.read_text(encoding="utf-8")
                for path in agent_frictions.iter_event_paths(store))
            self.assertNotIn("SECRET-PROMPT", persisted)
            self.assertNotIn("SECRET-TOOL-OUTPUT", persisted)
            self.assertNotIn('"message"', persisted)
            self.assertNotIn('"output"', persisted)
            cursor = json.loads((store / "cursors" /
                                 "thread-1.json").read_text(encoding="utf-8"))
            self.assertEqual(9, cursor["last_line"])

    def test_abort_is_deferred_and_list_can_filter_by_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            collected = agent_frictions.collect_events(rollout, store,
                                                        "unclaimed", self.now)

            rows = agent_frictions.list_events(store, "unclaimed", set(),
                                                "thread-1")["events"]
            aborted = next(row for row in rows
                           if row["event_type"] == "task_aborted")
            self.assertEqual("deferred", aborted["lifecycle"])
            self.assertTrue(all(row["source_id"] == "thread-1" for row in rows))
            self.assertEqual([], agent_frictions.list_events(
                store, None, set(), "another-thread")["events"])
            self.assertEqual(3, len(collected["created_event_ids"]))

    def test_open_summary_is_bounded_and_omits_long_fallbacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / "agent-frictions.md"
            inbox.write_text(
                "# Agent Frictions\n\n## Open\n\n"
                "### 2026-08-28 First\n"
                "- Signature：first.signature\n"
                "- 障碍：first short summary\n"
                "- fallback：SECRET-LONG-FALLBACK\n"
                "- 复现：2（legacy format）\n"
                "- 状态：open\n\n"
                "### 2026-08-27 Second\n"
                "- Signature：second.signature\n"
                "- 障碍：second short summary\n"
                "- 状态：open\n\n"
                "### 2026-08-26 Third\n"
                "- Signature：third.signature\n"
                "- 障碍：third short summary\n"
                "- 状态：open\n\n"
                "## Closed\n",
                encoding="utf-8")

            result = agent_frictions.open_summary(inbox, 2)

            self.assertEqual(3, result["open_count"])
            self.assertEqual(2, result["shown"])
            self.assertEqual("first.signature",
                             result["entries"][0]["signature"])
            self.assertEqual(2, result["entries"][0]["recurrence"])
            self.assertEqual(3, result["entries"][0]["occurrence_count"])
            self.assertEqual(
                "legacy_unbound", result["entries"][0]["identity_status"]
            )
            self.assertEqual(0, result["entries"][1]["recurrence"])
            self.assertEqual(1, result["entries"][1]["occurrence_count"])
            self.assertEqual(
                "legacy_unbound", result["entries"][1]["identity_status"]
            )
            self.assertNotIn("SECRET", json.dumps(result))

    def test_record_occurrence_is_idempotent_and_counts_distinct_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "agent-frictions.md"
            inbox.write_text(
                "# Agent Frictions\n\n## Open\n\n"
                "### 2026-09-04 Example\n"
                "- Signature：example.signature\n"
                "- 障碍：example\n"
                "- 状态：open\n\n"
                "## Closed\n",
                encoding="utf-8",
            )

            def write_settlement(name: str, thread_id: str) -> Path:
                settlement = root / f"{name}.json"
                identity = json.dumps(
                    {
                        "project_cwd": "/workspace/project",
                        "thread_id": thread_id,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                occurrence_key = (
                    "codex-thread-project:"
                    + hashlib.sha256(identity.encode()).hexdigest()
                )
                settlement.write_text(
                    json.dumps({
                        "schema": "save-context.audit-settlement.v1",
                        "audit_id": name,
                        "status": "settled",
                        "items": [
                            {
                                "lane": "execution_friction",
                                "audit_id": "candidate-a",
                                "disposition": "promoted",
                                "destination": "global_friction",
                                "signature": "example.signature",
                                "durable_ref": str(inbox) + "#examplesignature",
                            },
                            {
                                "lane": "prompt_contract_gaps",
                                "audit_id": "candidate-b",
                                "disposition": "promoted",
                                "destination": "global_friction",
                                "signature": "example.signature",
                                "durable_ref": str(inbox) + "#examplesignature",
                            },
                        ],
                        "occurrence": {
                            "kind": "codex_thread_project",
                            "key": occurrence_key,
                            "thread_id": thread_id,
                            "project_cwd": "/workspace/project",
                        },
                    }),
                    encoding="utf-8",
                )
                return settlement

            first_settlement = write_settlement("audit-first", "thread-1")
            with self.assertRaisesRegex(ValueError, "has no occurrence identity"):
                agent_frictions.record_occurrence(
                    inbox, first_settlement, "example.signature"
                )
            first = agent_frictions.record_occurrence(
                inbox, first_settlement, "example.signature", initialize=True
            )
            repeated = agent_frictions.record_occurrence(
                inbox, first_settlement, "example.signature", initialize=True
            )
            second = agent_frictions.record_occurrence(
                inbox,
                write_settlement("audit-second", "thread-2"),
                "example.signature",
            )

            self.assertTrue(first["updated"])
            self.assertEqual(1, first["occurrence_count"])
            self.assertEqual(0, first["recurrence"])
            self.assertFalse(repeated["updated"])
            self.assertEqual(1, repeated["occurrence_count"])
            self.assertTrue(second["updated"])
            self.assertEqual(2, second["occurrence_count"])
            self.assertEqual(1, second["recurrence"])
            content = inbox.read_text(encoding="utf-8")
            self.assertEqual(2, content.count("- Occurrence："))
            self.assertIn("- 复现：+1（最近：save-context-audit:audit-second）", content)

            first_write_ready = threading.Event()
            release_first = threading.Event()
            second_finished = threading.Event()
            original_write = agent_frictions.atomic_write_text

            def paused_write(path: Path, content: str) -> None:
                if '"thread_id":"thread-3"' in content and '"thread_id":"thread-4"' not in content:
                    first_write_ready.set()
                    if not release_first.wait(5):
                        raise RuntimeError("concurrent writer fixture timed out")
                original_write(path, content)

            third_input = write_settlement("audit-third", "thread-3")
            fourth_input = write_settlement("audit-fourth", "thread-4")

            def second_writer() -> dict:
                try:
                    return agent_frictions.record_occurrence(
                        inbox, fourth_input, "example.signature"
                    )
                finally:
                    second_finished.set()

            with patch.object(agent_frictions, "atomic_write_text", paused_write):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    third = pool.submit(agent_frictions.record_occurrence,
                                        inbox, third_input, "example.signature")
                    try:
                        self.assertTrue(first_write_ready.wait(5))
                        fourth = pool.submit(second_writer)
                        self.assertFalse(second_finished.wait(0.2))
                    finally:
                        release_first.set()
                    self.assertTrue(third.result(timeout=5)["updated"])
                    self.assertTrue(fourth.result(timeout=5)["updated"])
            content = inbox.read_text(encoding="utf-8")
            self.assertEqual(4, content.count("- Occurrence："))
            self.assertIn("- 复现：+3", content)

            duplicate = next(line for line in content.splitlines()
                             if line.startswith("- Occurrence："))
            damaged = content.replace(duplicate, duplicate + "\n" + duplicate, 1)
            inbox.write_text(damaged, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate occurrence identities"):
                agent_frictions.record_occurrence(inbox, fourth_input, "example.signature")
            self.assertEqual(damaged, inbox.read_text(encoding="utf-8"))

    def test_checkpoint_claim_and_owner_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            result = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                    self.now)
            first, second, _ = result["created_event_ids"]

            agent_frictions.checkpoint(store, [first], "context:amt:mainline",
                                       self.now)
            agent_frictions.checkpoint(store, [second], "context:amt:other",
                                       self.now)
            contract = temp / "contract.json"
            contract.write_text("{}\n", encoding="utf-8")
            claimed = agent_frictions.claim(store, "context:amt:mainline",
                                            str(contract), self.now)

            self.assertEqual([first], claimed["claimed_event_ids"])
            _, first_event = agent_frictions.find_event(store, first)
            _, second_event = agent_frictions.find_event(store, second)
            self.assertEqual("ll_contract", first_event["owner"]["kind"])
            self.assertEqual("context", first_event["claimed_from"]["kind"])
            self.assertEqual({
                "kind": "context",
                "id": "amt:other"
            }, second_event["owner"])
            status = agent_frictions.status_events(store, "context:amt:other")
            self.assertEqual(1, status["actionable_count"])
            self.assertEqual(1, sum(status["by_event_type"].values()))
            self.assertNotIn("facts", status)

    def test_status_excludes_deferred_from_actionable_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            collected = agent_frictions.collect_events(rollout, store,
                                                        "unclaimed", self.now)
            agent_frictions.checkpoint(store, collected["created_event_ids"],
                                       "context:amt:mainline", self.now)

            status = agent_frictions.status_events(
                store, "context:amt:mainline")

            self.assertEqual(1, status["actionable_count"])
            self.assertEqual({"deferred": 2, "pending": 1},
                             status["by_lifecycle"])
            self.assertEqual(3, sum(status["by_event_type"].values()))

    def test_new_aggregate_does_not_supersede_owned_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            first = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                   self.now)
            aggregate_id = next(
                event_id for event_id in first["created_event_ids"]
                if agent_frictions.find_event(store, event_id)[1]["event_type"]
                == "repeated_file_edit_candidate")
            agent_frictions.checkpoint(store, [aggregate_id],
                                       "context:amt:mainline", self.now)
            with rollout.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps({
                        "timestamp": "2026-07-13T01:07:00Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "patch_apply_end",
                            "turn_id": "turn-6",
                            "call_id": "call-5",
                            "success": True,
                            "changes": {
                                "/repo/a.md": {
                                    "kind": "update"
                                }
                            },
                        },
                    }) + "\n")

            second = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                    self.now)
            _, owned = agent_frictions.find_event(store, aggregate_id)
            self.assertEqual("context", owned["owner"]["kind"])
            self.assertEqual("deferred", owned["lifecycle"])
            self.assertEqual(0, second["superseded_events"])
            candidates = [
                event for event in self.all_events(store)
                if event["event_type"] == "repeated_file_edit_candidate"
            ]
            self.assertEqual(2, len(candidates))

    def test_settle_requires_explicit_resolution_and_writes_rollup(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            event_id = agent_frictions.collect_events(
                rollout, store, "unclaimed", self.now)["created_event_ids"][0]
            agent_frictions.checkpoint(store, [event_id],
                                       "context:amt:mainline", self.now)

            with self.assertRaisesRegex(ValueError,
                                        "belongs to context:amt:mainline"):
                agent_frictions.settle(store, event_id, "resolved", True, None,
                                       None, "human", False,
                                       "context:amt:other", self.now)

            preview = agent_frictions.settle(store, event_id, "resolved", True,
                                             "requirement_change", "用户主动迭代",
                                             "human", False,
                                             "context:amt:mainline", self.now)
            _, unchanged = agent_frictions.find_event(store, event_id)
            self.assertTrue(preview["dry_run"])
            self.assertNotEqual("resolved", unchanged["lifecycle"])

            result = agent_frictions.settle(store, event_id, "resolved", False,
                                            "requirement_change", "用户主动迭代",
                                            "human", False,
                                            "context:amt:mainline", self.now)
            _, settled = agent_frictions.find_event(store, event_id)
            self.assertEqual("resolved", settled["lifecycle"])
            self.assertEqual({
                "kind": "unclaimed",
                "id": None
            }, settled["owner"])
            self.assertEqual("context", settled["settled_from"]["kind"])
            rollup = Path(result["rollup_path"])
            self.assertEqual(
                1, len(rollup.read_text(encoding="utf-8").splitlines()))
            with self.assertRaisesRegex(ValueError, "already settled"):
                agent_frictions.checkpoint(store, [event_id],
                                           "context:amt:mainline", self.now)

    def test_cleanup_is_dry_run_and_separates_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            store = temp / "store"
            rollout = self.write_rollout(temp)
            ids = agent_frictions.collect_events(rollout, store, "unclaimed",
                                                 self.now)["created_event_ids"]
            settled_id, orphan_id, incident_id = ids
            agent_frictions.settle(store, settled_id, "resolved", False, None,
                                   None, "human", False, "unclaimed", self.now)
            agent_frictions.settle(store, incident_id, "ignored", False, None,
                                   None, "human", True, "unclaimed", self.now)

            _, orphan = agent_frictions.find_event(store, orphan_id)
            orphan["last_owner_seen_at"] = agent_frictions.isoformat(
                self.now - timedelta(days=31))
            orphan_path, _ = agent_frictions.find_event(store, orphan_id)
            agent_frictions.atomic_write_json(orphan_path, orphan)

            report = agent_frictions.cleanup_dry_run(
                store, temp / "ai-home", self.now + timedelta(days=31))
            settled_path, _ = agent_frictions.find_event(store, settled_id)
            incident_path, _ = agent_frictions.find_event(store, incident_id)
            self.assertIn(str(settled_path), report["delete_paths"])
            self.assertNotIn(str(incident_path), report["delete_paths"])
            self.assertIn(str(orphan_path), report["orphan_review_paths"])
            self.assertTrue(settled_path.exists())

            contract = temp / "active-contract.json"
            contract.write_text(
                json.dumps({"ll_contract": {
                    "exit": {
                        "state": "active"
                    }
                }}) + "\n",
                encoding="utf-8")
            agent_frictions.checkpoint(store, [orphan_id],
                                       f"ll-contract:{contract}", self.now)
            protected = agent_frictions.cleanup_dry_run(
                store, temp / "ai-home", self.now + timedelta(days=31))
            self.assertIn(str(orphan_path), protected["protected_paths"])
            self.assertNotIn(str(orphan_path), protected["orphan_review_paths"])


if __name__ == "__main__":
    unittest.main()
