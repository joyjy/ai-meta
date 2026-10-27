#!/usr/bin/env python3
"""Regression tests for save_context_recover.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from save_context_recover import build_packet, locate_rollout  # noqa: E402

PACKET_ARGS = argparse.Namespace(max_messages=8, max_tool_calls=30, max_paths=25,
                                 max_context_blocks=3, max_text_chars=1200,
                                 max_context_chars=12000)


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
                        "---\n# context: project=amt; mainline=active; workstreams=0()\nproject: amt\n---\n",
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

    def test_recovery_packet_dedupes_mirrored_messages_and_omits_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            rollout = self.write_rollout(codex_home)

            packet = build_packet(rollout, PACKET_ARGS)

            self.assertIn("session_id: `thread-1`", packet)
            self.assertIn("git status --short", packet)
            self.assertEqual(1, packet.count("save context"))
            self.assertIn("call=call-status status=success", packet)
            self.assertIn("exit_code=0", packet)
            self.assertIn("result_chars=11", packet)
            self.assertNotIn(" M file.py", packet)
            self.assertIn("exec_command: python3 -m unittest", packet)
            self.assertIn("call=call-wrapper status=success", packet)
            self.assertIn("result_chars=19", packet)
            self.assertNotIn("secret test details", packet)
            self.assertIn("project=amt", packet)
            self.assertIn("turn_aborted: 1", packet)

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

            packet = build_packet(rollout, PACKET_ARGS)

            self.assertEqual(1, packet.count("### 2026-07-27T01:00:00Z"))
            self.assertIn("first\nsecond", packet)
            self.assertIn("call=call-fail status=failed", packet)
            self.assertIn("exit_code=1", packet)
            self.assertNotIn("sensitive failure details", packet)

    def test_locate_rollout_finds_archived_thread(self) -> None:
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

            self.assertEqual(rollout, locate_rollout(codex_home, None, "thread-2"))


if __name__ == "__main__":
    unittest.main()
