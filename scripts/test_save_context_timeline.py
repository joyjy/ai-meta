#!/usr/bin/env python3
"""Regression tests for save_context_timeline.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("save_context_timeline.py")


class SaveContextTimelineTest(unittest.TestCase):

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["TZ"] = "Asia/Shanghai"
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def write_rollout(self,
                      path: Path,
                      events: list[dict[str, object]],
                      *,
                      malformed: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(event) for event in events]
        if malformed:
            lines.insert(2, "{malformed")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def user_message(self,
                     timestamp: str,
                     text: str,
                     *,
                     turn_id: str | None = None,
                     message_id: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "type": "message",
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": text,
            }],
        }
        if message_id:
            payload["id"] = message_id
        if turn_id:
            payload["internal_chat_message_metadata_passthrough"] = {
                "turn_id": turn_id,
            }
        return {
            "timestamp": timestamp,
            "type": "response_item",
            "payload": payload,
        }

    def test_rollout_entry_deduplicates_and_emits_stable_local_schema(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            events: list[dict[str, object]] = [
                {
                    "timestamp": "2026-07-23T00:50:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "thread-rollout",
                    },
                },
                self.user_message(
                    "2026-07-23T00:51:00Z",
                    "<recommended_plugins>\nclient context",
                    turn_id="turn-load-only",
                    message_id="message-load-context-a",
                ),
                self.user_message(
                    "2026-07-23T00:51:00.010Z",
                    "[$load-context](/tmp/load-context/SKILL.md) amt",
                    turn_id="turn-load-only",
                    message_id="message-load-context-b",
                ),
                self.user_message(
                    "2026-07-23T00:51:00.020Z",
                    "<skill>\n<name>load-context</name>",
                    turn_id="turn-load-only",
                    message_id="message-load-context-c",
                ),
                self.user_message(
                    "2026-07-23T01:00:00Z",
                    "later",
                    turn_id="turn-later",
                    message_id="message-later",
                ),
                {
                    "timestamp": "2026-07-23T00:59:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{
                            "type": "output_text",
                            "text": "ignore",
                        }],
                    },
                },
                {
                    "timestamp": "2026-07-23T00:59:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "developer",
                        "content": [{
                            "type": "input_text",
                            "text": "ignore",
                        }],
                    },
                },
                {
                    "timestamp": "2026-07-23T00:59:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "not role=user",
                    },
                },
                {
                    "timestamp": "2026-07-23T00:59:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                    },
                },
                {
                    "timestamp": "2026-07-23T00:59:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "output": "ignore",
                    },
                },
                self.user_message(
                    "2026-07-23T00:52:58.311Z",
                    "first part",
                    turn_id="turn-first",
                    message_id="message-first-a",
                ),
                self.user_message(
                    "2026-07-23T00:52:58.373Z",
                    "same desktop turn",
                    turn_id="turn-first",
                    message_id="message-first-b",
                ),
                self.user_message("2026-07-23T00:55:00Z", "no ids"),
                self.user_message("2026-07-23T00:55:00Z", "no ids"),
                self.user_message(
                    "2026-07-23T00:56:00Z",
                    "same message id",
                    message_id="message-stable",
                ),
                self.user_message(
                    "2026-07-23T00:56:01Z",
                    "same message id copied",
                    message_id="message-stable",
                ),
            ]
            self.write_rollout(rollout, events, malformed=True)

            proc = self.run_script("--rollout", str(rollout))

            self.assertEqual(0, proc.returncode, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(
                [
                    "thread_id",
                    "timezone",
                    "first_user_at",
                    "last_user_at",
                    "user_message_count",
                    "excluded_control_turn_count",
                    "checkpoints",
                    "checkpoint_at",
                ],
                list(data),
            )
            self.assertEqual("thread-rollout", data["thread_id"])
            self.assertEqual("Asia/Shanghai", data["timezone"])
            self.assertEqual("2026-07-23T08:52:58.311+08:00",
                             data["first_user_at"])
            self.assertEqual("2026-07-23T09:00:00.000+08:00",
                             data["last_user_at"])
            self.assertEqual(data["last_user_at"], data["checkpoint_at"])
            self.assertEqual(4, data["user_message_count"])
            self.assertEqual(1, data["excluded_control_turn_count"])
            self.assertEqual(
                [
                    {
                        "date": "2026-07-23",
                        "checkpoint_at": "2026-07-23T09:00:00.000+08:00",
                    },
                ],
                data["checkpoints"],
            )
            self.assertNotIn("user_points", data)

            points_proc = self.run_script("--rollout", str(rollout),
                                          "--include-points")

            self.assertEqual(0, points_proc.returncode, points_proc.stderr)
            points_data = json.loads(points_proc.stdout)
            self.assertEqual("user_points", list(points_data)[-1])
            self.assertEqual(
                [
                    "2026-07-23T08:52:58.311+08:00",
                    "2026-07-23T08:55:00.000+08:00",
                    "2026-07-23T08:56:00.000+08:00",
                    "2026-07-23T09:00:00.000+08:00",
                ],
                [point["timestamp"] for point in points_data["user_points"]],
            )

    def test_load_context_turn_with_real_request_is_not_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            self.write_rollout(rollout, [
                {
                    "timestamp": "2026-07-23T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "thread-load-and-work",
                    },
                },
                self.user_message(
                    "2026-07-23T00:01:00Z",
                    "/load-context amt",
                    turn_id="turn-load-and-work",
                ),
                self.user_message(
                    "2026-07-23T00:01:00.010Z",
                    "然后继续修 timeline",
                    turn_id="turn-load-and-work",
                ),
            ])

            proc = self.run_script("--rollout", str(rollout))

            self.assertEqual(0, proc.returncode, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(1, data["user_message_count"])
            self.assertEqual(0, data["excluded_control_turn_count"])
            self.assertEqual("2026-07-23T08:01:00.000+08:00",
                             data["first_user_at"])

    def test_summary_keeps_latest_checkpoint_for_each_local_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            self.write_rollout(rollout, [
                {
                    "timestamp": "2026-07-23T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "thread-multiday",
                    },
                },
                self.user_message(
                    "2026-07-23T15:50:00Z",
                    "day one",
                    turn_id="turn-day-one",
                ),
                self.user_message(
                    "2026-07-23T16:01:00Z",
                    "day two first",
                    turn_id="turn-day-two-first",
                ),
                self.user_message(
                    "2026-07-23T16:03:00Z",
                    "day two latest",
                    turn_id="turn-day-two-latest",
                ),
            ])

            proc = self.run_script("--rollout", str(rollout))

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(
                [
                    {
                        "date": "2026-07-23",
                        "checkpoint_at": "2026-07-23T23:50:00.000+08:00",
                    },
                    {
                        "date": "2026-07-24",
                        "checkpoint_at": "2026-07-24T00:03:00.000+08:00",
                    },
                ],
                json.loads(proc.stdout)["checkpoints"],
            )

    def test_thread_id_entry_locates_archived_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            rollout = (codex_home / "archived_sessions" /
                       "rollout-2026-07-23T00-00-00-thread-archived.jsonl")
            self.write_rollout(rollout, [
                {
                    "timestamp": "2026-07-23T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "session_id": "thread-archived",
                    },
                },
                self.user_message(
                    "2026-07-23T00:01:00Z",
                    "hello",
                    turn_id="turn-1",
                ),
            ])

            proc = self.run_script(
                "--codex-home",
                str(codex_home),
                "--thread-id",
                "thread-archived",
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual("thread-archived",
                             json.loads(proc.stdout)["thread_id"])

    def test_non_user_rollout_reports_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            self.write_rollout(
                rollout,
                [
                    {
                        "timestamp": "2026-07-23T00:00:00Z",
                        "type": "session_meta",
                        "payload": {
                            "id": "thread-empty",
                        },
                    },
                    {
                        "timestamp": "2026-07-23T00:01:00Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "system",
                            "content": [],
                        },
                    },
                ],
                malformed=True,
            )

            proc = self.run_script("--rollout", str(rollout))

            self.assertEqual(1, proc.returncode)
            self.assertIn("no role=user messages found", proc.stderr)
            self.assertEqual("", proc.stdout)


if __name__ == "__main__":
    unittest.main()
