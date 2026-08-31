#!/usr/bin/env python3
"""Regression tests for save_context_recover.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("save_context_recover.py")


class SaveContextRecoverTest(unittest.TestCase):

    def write_rollout(self, root: Path, thread_id: str = "thread-1") -> Path:
        rollout = root / "sessions" / "2026" / "06" / "24" / f"rollout-2026-06-24T01-02-03-{thread_id}.jsonl"
        rollout.parent.mkdir(parents=True)
        events = [
            {
                "timestamp": "2026-06-24T01:00:00Z",
                "type": "session_meta",
                "payload": {
                    "session_id": thread_id,
                    "cwd": "/Users/example/project",
                    "originator": "Codex Desktop",
                    "model": "gpt-test",
                },
            },
            {
                "timestamp": "2026-06-24T01:01:00Z",
                "type": "event_msg",
                "payload": {
                    "type": "user_message",
                    "message": "save context",
                },
            },
            {
                "timestamp": "2026-06-24T01:01:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "internal_chat_message_metadata_passthrough": {
                        "turn_id": "turn-save",
                    },
                    "content": [{
                        "type": "input_text",
                        "text": "save context",
                    }],
                },
            },
            {
                "timestamp": "2026-06-24T01:02:00Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "functions.exec_command",
                    "call_id": "call-status",
                    "input": json.dumps({"cmd": "git status --short"}),
                },
            },
            {
                "timestamp": "2026-06-24T01:02:01Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "call_id": "call-status",
                    "output": json.dumps({
                        "exit_code": 0,
                        "output": " M file.py\n",
                    }),
                },
            },
            {
                "timestamp": "2026-06-24T01:02:02Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "exec",
                    "call_id": "call-wrapper",
                    "input": 'const r = await tools.exec_command({cmd:"python3 -m unittest", yield_time_ms:10000});text(r);',
                },
            },
            {
                "timestamp": "2026-06-24T01:02:03Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "call_id": "call-wrapper",
                    "output": [{
                        "type": "input_text",
                        "text": "Script completed\nWall time 0.1 seconds\nOutput:\n",
                    }, {
                        "type": "input_text",
                        "text": json.dumps({
                            "exit_code": 0,
                            "output": "secret test details",
                        }),
                    }],
                },
            },
            {
                "timestamp": "2026-06-24T01:03:00Z",
                "type": "response_item",
                "payload": {
                    "type":
                    "message",
                    "role":
                    "assistant",
                    "content": [{
                        "type":
                        "output_text",
                        "text":
                        "---\n# context: project=amt; mainline=active; workstreams=0(); next=mainline\nproject: amt\n---\n",
                    }],
                },
            },
            {
                "timestamp": "2026-06-24T01:04:00Z",
                "type": "turn_aborted",
                "payload": {},
            },
        ]
        rollout.write_text("".join(
            json.dumps(event) + "\n" for event in events),
                           encoding="utf-8")
        return rollout

    def test_recovery_packet_from_rollout_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            rollout = self.write_rollout(codex_home)

            proc = subprocess.run(
                [sys.executable,
                 str(SCRIPT), "--rollout",
                 str(rollout)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn("session_id: `thread-1`", proc.stdout)
            self.assertIn("git status --short", proc.stdout)
            self.assertEqual(1, proc.stdout.count("save context"))
            self.assertIn("call=call-status status=success", proc.stdout)
            self.assertIn("exit_code=0", proc.stdout)
            self.assertIn("result_chars=11", proc.stdout)
            self.assertNotIn(" M file.py", proc.stdout)
            self.assertIn("exec_command: python3 -m unittest", proc.stdout)
            self.assertIn("call=call-wrapper status=success", proc.stdout)
            self.assertIn("result_chars=19", proc.stdout)
            self.assertNotIn("secret test details", proc.stdout)
            self.assertIn("project=amt", proc.stdout)
            self.assertIn("turn_aborted: 1", proc.stdout)

    def test_recovery_packet_groups_same_turn_and_reports_failed_tool_span(
            self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            events = [
                {
                    "timestamp": "2026-07-27T01:00:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "internal_chat_message_metadata_passthrough": {
                            "turn_id": "turn-1",
                        },
                        "content": [{"type": "input_text", "text": "first"}],
                    },
                },
                {
                    "timestamp": "2026-07-27T01:00:00.010Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "internal_chat_message_metadata_passthrough": {
                            "turn_id": "turn-1",
                        },
                        "content": [{"type": "input_text", "text": "second"}],
                    },
                },
                {
                    "timestamp": "2026-07-27T01:01:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "call_id": "call-fail",
                        "input": json.dumps({"cmd": "false"}),
                    },
                },
                {
                    "timestamp": "2026-07-27T01:01:01Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "call-fail",
                        "output": json.dumps({
                            "exit_code": 1,
                            "output": "sensitive failure details",
                        }),
                    },
                },
            ]
            rollout.write_text("".join(
                json.dumps(event) + "\n" for event in events),
                               encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--rollout", str(rollout)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertEqual(1, proc.stdout.count("### 2026-07-27T01:00:00Z"))
            self.assertIn("first\nsecond", proc.stdout)
            self.assertIn("call=call-fail status=failed", proc.stdout)
            self.assertIn("exit_code=1", proc.stdout)
            self.assertNotIn("sensitive failure details", proc.stdout)

    def test_recovery_packet_locates_archived_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            archived = codex_home / "archived_sessions"
            archived.mkdir()
            rollout = archived / "rollout-2026-06-24T01-02-03-thread-2.jsonl"
            rollout.write_text(
                json.dumps({
                    "timestamp": "2026-06-24T01:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "session_id": "thread-2",
                    },
                }) + "\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--codex-home",
                    str(codex_home),
                    "--thread-id",
                    "thread-2",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn(str(rollout), proc.stdout)

    def test_recovery_packet_keeps_legacy_context_support(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "legacy.jsonl"
            rollout.write_text(
                json.dumps({
                    "timestamp": "2026-06-24T01:00:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{
                            "type": "output_text",
                            "text": "<!-- context: project=old; mainline=active; workstreams=0(); next=mainline -->\n\n---\nproject: old\n---\n",
                        }],
                    },
                }) + "\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--rollout", str(rollout)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn("project=old", proc.stdout)


if __name__ == "__main__":
    unittest.main()
