#!/usr/bin/env python3
"""Regression tests for the stable GitLab CI facade."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import unittest


SCRIPT = Path(__file__).with_name("gitlab-ci")


def load_module():
    loader = importlib.machinery.SourceFileLoader("gitlab_ci", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class GitlabCiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def parse(self, *args: str):
        return self.mod.build_parser().parse_args(args)

    def test_list_maps_ref_to_installed_glab_syntax(self):
        cmd = self.mod.build_command(
            self.parse("list", "--ref", "feat/test", "--status", "failed")
        )

        self.assertEqual(
            [
                "glab", "ci", "list", "--output", "json", "--ref",
                "feat/test", "--status", "failed", "--per-page", "30",
            ],
            cmd,
        )

    def test_trace_is_noninteractive_when_job_is_explicit(self):
        cmd = self.mod.build_command(
            self.parse("trace", "lint", "--pipeline-id", "456")
        )

        self.assertEqual(
            ["glab", "ci", "trace", "lint", "--pipeline-id", "456"],
            cmd,
        )

if __name__ == "__main__":
    unittest.main()
