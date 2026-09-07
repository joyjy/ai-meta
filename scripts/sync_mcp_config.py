#!/usr/bin/env python3
"""Publish compatible shared remote MCP entries into Codex's managed block."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


BEGIN_MARKER = "# ai-meta:mcp:begin"
END_MARKER = "# ai-meta:mcp:end"
CODEX_NATIVE_OAUTH_SERVERS = frozenset({"meego"})
TABLE_PATTERN = re.compile(
    r'^\s*\[\s*mcp_servers\.(?:"((?:[^"\\]|\\.)*)"|([A-Za-z0-9_-]+))\s*\]\s*(?:#.*)?$'
)


class SyncError(ValueError):
    """Raised when inputs cannot be synchronized without losing configuration."""


def toml_string(value: str) -> str:
    """Encode a string using TOML-compatible JSON basic-string escaping."""
    return json.dumps(value, ensure_ascii=True)


def load_remote_servers(source: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SyncError(f"shared MCP config does not exist: {source}") from error
    except json.JSONDecodeError as error:
        raise SyncError(
            f"shared MCP config is invalid JSON at line {error.lineno}, column {error.colno}"
        ) from error

    raw_servers = payload.get("mcp") if isinstance(payload, dict) else None
    if not isinstance(raw_servers, dict):
        raise SyncError("shared MCP config must contain an object at key 'mcp'")

    servers: dict[str, dict[str, Any]] = {}
    for name, raw_server in sorted(raw_servers.items()):
        if not isinstance(name, str) or not name:
            raise SyncError("MCP server names must be non-empty strings")
        if not isinstance(raw_server, dict):
            raise SyncError(f"MCP server {name!r} must be an object")
        if raw_server.get("type") != "remote":
            continue

        if name in CODEX_NATIVE_OAUTH_SERVERS:
            # These servers use Codex's native OAuth store and stay outside the
            # generated block so shared access tokens cannot override OAuth.
            continue

        url = raw_server.get("url")
        if not isinstance(url, str) or not url:
            raise SyncError(f"remote MCP server {name!r} must define a non-empty URL")
        headers = raw_server.get("headers", {})
        if not isinstance(headers, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in headers.items()
        ):
            raise SyncError(f"remote MCP server {name!r} headers must be string pairs")

        servers[name] = {"url": url, "headers": headers}

    return servers


def remove_managed_block(config: str) -> str:
    begin_count = config.count(BEGIN_MARKER)
    end_count = config.count(END_MARKER)
    if begin_count != end_count or begin_count > 1:
        raise SyncError("Codex config contains malformed ai-meta MCP markers")
    if begin_count == 0:
        return config

    before, remainder = config.split(BEGIN_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    return (before.rstrip() + "\n" + after.lstrip("\n")).rstrip() + "\n"


def existing_server_names(config: str) -> set[str]:
    names: set[str] = set()
    for line in config.splitlines():
        match = TABLE_PATTERN.match(line)
        if not match:
            continue
        quoted, bare = match.groups()
        if bare is not None:
            names.add(bare)
            continue
        try:
            names.add(json.loads(f'"{quoted}"'))
        except json.JSONDecodeError as error:
            raise SyncError("Codex config has an invalid quoted MCP server name") from error
    return names


def render_managed_block(servers: dict[str, dict[str, Any]]) -> str:
    lines = [BEGIN_MARKER, "# Generated from ~/.ai/mcp/config.json; do not edit this block."]
    for name, server in servers.items():
        lines.extend(
            [
                "",
                f"[mcp_servers.{toml_string(name)}]",
                f"url = {toml_string(server['url'])}",
            ]
        )
        headers = server["headers"]
        if headers:
            pairs = ", ".join(
                f"{toml_string(key)} = {toml_string(value)}"
                for key, value in sorted(headers.items())
            )
            lines.append(f"http_headers = {{ {pairs} }}")
    lines.extend(["", END_MARKER])
    return "\n".join(lines)


def build_config(existing: str, servers: dict[str, dict[str, Any]]) -> str:
    unmanaged = remove_managed_block(existing)
    conflicts = sorted(existing_server_names(unmanaged).intersection(servers))
    if conflicts:
        raise SyncError(
            "Codex config already defines unmanaged MCP server(s): "
            + ", ".join(conflicts)
        )

    prefix = unmanaged.rstrip()
    block = render_managed_block(servers)
    return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(temp_path, (mode & 0o600) or 0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish compatible shared remote MCP entries into Codex config; "
            "servers assigned to native Codex OAuth stay client-owned."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("~/.ai/mcp/config.json").expanduser(),
        help="shared MCP JSON source",
    )
    parser.add_argument(
        "--codex-config",
        type=Path,
        default=Path("~/.codex/config.toml").expanduser(),
        help="Codex TOML config to update",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and report the managed server names without writing",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser()
    codex_config = args.codex_config.expanduser()
    try:
        servers = load_remote_servers(source)
        existing = (
            codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
        )
        rendered = build_config(existing, servers)
    except (OSError, SyncError) as error:
        print(f"sync-mcp-config: error: {error}", file=sys.stderr)
        return 1

    names = ", ".join(servers) if servers else "none"
    if args.dry_run:
        print(f"sync-mcp-config: would manage {len(servers)} server(s): {names}")
        return 0

    try:
        write_atomic(codex_config, rendered)
    except OSError as error:
        print(f"sync-mcp-config: error: {error}", file=sys.stderr)
        return 1
    print(f"sync-mcp-config: managed {len(servers)} server(s): {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
