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

    def setUp(self) -> None:
        usage = tempfile.TemporaryDirectory()
        self.addCleanup(usage.cleanup)
        self.usage_dir = usage.name

    def run_script(self, *args: str,
                   env_extra: dict[str, str] | None = None
                   ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["TZ"] = "Asia/Shanghai"
        env["AI_META_USAGE_DIR"] = self.usage_dir
        env.update(env_extra or {})
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

    def test_rollout_entry_deduplicates_and_emits_stable_local_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            events = [
                {"timestamp": "2026-07-23T00:50:00Z", "type": "session_meta",
                 "payload": {"id": "thread-rollout"}},
                self.user_message("2026-07-23T00:51:00Z",
                                  "<recommended_plugins>\nclient context",
                                  turn_id="turn-load-only"),
                self.user_message("2026-07-23T00:51:00.010Z",
                                  "[$load-context](/tmp/load-context/SKILL.md) amt",
                                  turn_id="turn-load-only"),
                self.user_message("2026-07-23T00:52:58.311Z", "first part",
                                  turn_id="turn-first"),
                self.user_message("2026-07-23T00:52:58.373Z", "same desktop turn",
                                  turn_id="turn-first"),
                self.user_message("2026-07-23T01:00:00Z", "later",
                                  turn_id="turn-later"),
                {"timestamp": "2026-07-23T01:30:00Z", "type": "response_item",
                 "payload": {"type": "message", "role": "assistant",
                             "content": [{"type": "output_text", "text": "ignore"}]}},
                {"timestamp": "2026-07-23T01:30:00Z", "type": "event_msg",
                 "payload": {"type": "user_message", "message": "not role=user"}},
            ]
            self.write_rollout(rollout, events, malformed=True)
            proc = self.run_script("--rollout", str(rollout))
            self.assertEqual(0, proc.returncode, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual("thread-rollout", data["thread_id"])
            self.assertEqual("2026-07-23T08:52:58.311+08:00", data["first_user_at"])
            self.assertEqual("2026-07-23T09:00:00.000+08:00", data["last_user_at"])
            self.assertEqual(data["last_user_at"], data["checkpoint_at"])
            self.assertEqual(2, data["user_message_count"])
            self.assertEqual(1, data["excluded_control_turn_count"])
            self.assertNotIn("user_points", data)

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

    def test_claude_session_counts_only_typed_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            transcript = projects / "-repo" / "session-1.jsonl"

            def user(timestamp: str, content: object,
                     **fields: object) -> dict[str, object]:
                return {"type": "user", "sessionId": "session-1",
                        "uuid": f"u-{timestamp}", "timestamp": timestamp,
                        "message": {"role": "user", "content": content},
                        **fields}

            self.write_rollout(transcript, [
                user("2026-07-23T00:50:00Z",
                     "<command-message>load-context</command-message>\n"
                     "<command-name>/load-context</command-name>\n"
                     "<command-args>amt</command-args>",
                     turnOrigin="human"),
                user("2026-07-23T00:50:01Z",
                     [{"type": "text", "text": "skill body"}], isMeta=True),
                user("2026-07-23T00:52:00Z", "first request", turnOrigin="human"),
                user("2026-07-23T00:53:00Z",
                     [{"type": "tool_result", "content": "ok"}]),
                user("2026-07-23T00:54:00Z", "<task-notification>done",
                     turnOrigin="task_notification"),
                user("2026-07-23T00:55:00Z", "<bash-stdout>x</bash-stdout>"),
                user("2026-07-23T00:56:00Z", "summary", isCompactSummary=True),
                user("2026-07-23T01:00:00Z",
                     [{"type": "text", "text": "later"}], turnOrigin="human"),
            ], malformed=True)

            proc = self.run_script(
                "--claude-session", "--claude-projects", str(projects),
                env_extra={"CLAUDE_CODE_SESSION_ID": "session-1"})

            self.assertEqual(0, proc.returncode, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual("session-1", data["thread_id"])
            self.assertEqual("2026-07-23T08:52:00.000+08:00", data["first_user_at"])
            self.assertEqual("2026-07-23T09:00:00.000+08:00", data["checkpoint_at"])
            self.assertEqual(2, data["user_message_count"])
            self.assertEqual(1, data["excluded_control_turn_count"])


if __name__ == "__main__":
    unittest.main()
