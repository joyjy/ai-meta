#!/usr/bin/env python3
"""Tests for sync-mcp-config's config-preserving write path."""

from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync-mcp-config")


class SyncMcpConfigTest(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "shared.json"
        self.codex_config = self.root / "config.toml"
        self.source.write_text(
            json.dumps(
                {
                    "mcp": {
                        "meego": {
                            "type": "remote",
                            "url": "https://example.test/mcp",
                            "headers": {"Authorization": "Bearer secret-token"},
                            "_oauth": {"refresh_token": "<test-redacted-token>"},
                        },
                        "local-only": {"type": "stdio", "command": "example"},
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_sync(
        self, *extra_args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(SCRIPT),
                "--source",
                str(self.source),
                "--codex-config",
                str(self.codex_config),
                *extra_args,
            ],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_sync_preserves_unmanaged_config_and_publishes_remote_server(self) -> None:
        self.codex_config.write_text('model = "gpt-test"\n', encoding="utf-8")
        self.codex_config.chmod(0o644)

        result = self.run_sync()

        config = self.codex_config.read_text(encoding="utf-8")
        self.assertIn('model = "gpt-test"', config)
        self.assertIn('[mcp_servers."meego"]', config)
        self.assertIn('"Authorization" = "Bearer secret-token"', config)
        self.assertNotIn("<test-redacted-token>", config)
        self.assertNotIn("local-only", config)
        self.assertNotIn("secret-token", result.stdout)
        self.assertEqual(stat.S_IMODE(self.codex_config.stat().st_mode), 0o600)

    def test_sync_is_idempotent(self) -> None:
        self.run_sync()
        first = self.codex_config.read_text(encoding="utf-8")

        self.run_sync()

        self.assertEqual(self.codex_config.read_text(encoding="utf-8"), first)
        self.assertEqual(first.count("# ai-meta:mcp:begin"), 1)

    def test_sync_rejects_unmanaged_name_collision(self) -> None:
        self.codex_config.write_text(
            '[mcp_servers.meego]\nurl = "https://manual.test/mcp"\n',
            encoding="utf-8",
        )
        original = self.codex_config.read_text(encoding="utf-8")

        result = self.run_sync(check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unmanaged MCP server(s): meego", result.stderr)
        self.assertEqual(self.codex_config.read_text(encoding="utf-8"), original)

    def test_dry_run_validates_without_creating_config(self) -> None:
        result = self.run_sync("--dry-run")

        self.assertIn("would manage 1 server(s): meego", result.stdout)
        self.assertFalse(self.codex_config.exists())


if __name__ == "__main__":
    unittest.main()
