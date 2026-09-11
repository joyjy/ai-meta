#!/usr/bin/env python3
"""Portable distribution tests for route-context resolution."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_context_resolve as resolver


REPO_ROOT = resolver.REPO_ROOT
ROUTE_CONFIG = REPO_ROOT / "route-context.json"


class PortableRouteContextResolveTest(unittest.TestCase):

    def setUp(self) -> None:
        self.local_route_tmp = tempfile.TemporaryDirectory()
        self.local_route_path = (
            Path(self.local_route_tmp.name) / "route-context.local.json"
        )
        self.env_patcher = patch.dict(os.environ, {
            "AI_META_ROUTE_CONTEXT_PATH": str(ROUTE_CONFIG),
            "AI_META_ROUTE_CONTEXT_LOCAL_PATH": str(self.local_route_path),
        })
        self.env_patcher.start()

    def tearDown(self) -> None:
        self.env_patcher.stop()
        self.local_route_tmp.cleanup()

    def test_amt_prefers_declared_project_with_checkout_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            me_root = Path(tmp)
            with patch.object(resolver, "ME_ROOT", me_root):
                fallback = resolver.resolve_route_context("处理 amt", REPO_ROOT)
            self.assertEqual(str(REPO_ROOT), fallback["primary_project"]["root"])
            other_root = me_root / "Projects/other-ai-meta"
            other_root.mkdir(parents=True)
            (other_root / "index.md").write_text("abbr: amt\n", encoding="utf-8")
            with patch.object(resolver, "ME_ROOT", me_root):
                result = resolver.resolve_route_context("处理 amt", REPO_ROOT)

        self.assertEqual(str(other_root), result["primary_project"]["root"])

    def test_portable_base_routes_are_available(self) -> None:
        cases = {
            "写一个 plan 文档": "plan-draft-document-placement",
            "运行 ./gradlew test": "gradle-wrapper-local-cache",
            "MCP 工具没挂载": "mcp-capability-discovery",
            "检查 localhost 监听": "loopback-integration",
        }
        for prompt, route_id in cases.items():
            with self.subTest(prompt=prompt):
                result = resolver.resolve_route_context(prompt, REPO_ROOT)
                self.assertTrue(any(
                    route["id"] == route_id
                    for route in result["special_routes"]
                ))

    def test_local_route_overrides_portable_base_by_id(self) -> None:
        self.local_route_path.write_text(json.dumps({
            "version": 1,
            "path_routes": [],
            "special_routes": [{
                "id": "gradle-wrapper-local-cache",
                "match": {"keywords": ["./gradlew"]},
                "route": {
                    "id": "gradle-wrapper-local-cache",
                    "name": "Local Gradle policy",
                    "notes": ["machine-local override"],
                },
            }],
        }), encoding="utf-8")

        result = resolver.resolve_route_context("运行 ./gradlew test", REPO_ROOT)

        route = next(
            route for route in result["special_routes"]
            if route["id"] == "gradle-wrapper-local-cache"
        )
        self.assertEqual("Local Gradle policy", route["name"])


if __name__ == "__main__":
    unittest.main()
