#!/usr/bin/env python3
"""Regression tests for wt_sweep.py: verdicts and the guarded remove path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("wt_sweep.py")
sys.path.insert(0, str(SCRIPT.parent))
import wt_sweep  # noqa: E402
FAKE_GLAB = """#!/usr/bin/env python3
import json, os, sys
branch = sys.argv[sys.argv.index("--source-branch") + 1]
print(json.dumps(json.load(open(os.environ["FAKE_MRS"])).get(branch, [])))
"""


class WtSweepTest(unittest.TestCase):

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.root = self.tmp / "projects"
        self.main = self.root / "app"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "glab").write_text(FAKE_GLAB)
        (bin_dir / "glab").chmod(0o755)
        self.mrs = self.tmp / "mrs.json"
        self.registry = self.tmp / "registry.md"
        self.registry.write_text("")
        self.env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", FAKE_MRS=str(self.mrs),
                        AI_META_USAGE_DIR=str(self.tmp / "usage"))
        self.main.mkdir(parents=True)
        self.git(self.main, "init", "-q", "-b", "master")
        (self.main / "AGENTS.md").write_text("# app\n")
        (self.main / ".gitignore").write_text("build/\nnode_modules/\n")
        self.git(self.main, "add", ".")
        self.git(self.main, "commit", "-qm", "init")
        self.git(self.main, "update-ref", "refs/remotes/origin/master", "HEAD")
        self.git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/master")

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def worktree(self, name: str, state: str | None) -> Path:
        path = self.root / f"app-wt-{name}"
        self.git(self.main, "worktree", "add", "-q", "-b", name, str(path))
        (path / f"{name}.txt").write_text(name)
        self.git(path, "add", ".")
        self.git(path, "commit", "-qm", name)
        mrs = json.loads(self.mrs.read_text()) if self.mrs.exists() else {}
        if state:
            mrs[name] = [{"iid": 1, "state": state, "sha": self.git(path, "rev-parse", "HEAD"),
                          "created_at": "2026-10-01T00:00:00Z", "merged_at": "2026-10-02T00:00:00Z"}]
        self.mrs.write_text(json.dumps(mrs))
        return path

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root),
                               "--registry", str(self.registry)],
                              capture_output=True, text=True, env=self.env)

    def test_list_verdicts(self) -> None:
        merged = self.worktree("merged", "merged")
        (merged / "node_modules").symlink_to(self.main)  # removing a link never reaches the repo behind it
        opened = self.worktree("opened", "opened")
        ops = self.worktree("ops", "merged")
        nested = self.worktree("nested", "merged")
        (nested / "vendor").mkdir()
        self.git(nested / "vendor", "init", "-q")
        (ops / "script" / "runs").mkdir(parents=True)
        (ops / "script" / "runs" / "r.jsonl").write_text("{}")
        deps = self.worktree("deps", "merged")
        (deps / "node_modules" / "es-abstract" / "operations").mkdir(parents=True)  # npm package, not a record
        noted = self.worktree("noted", "merged")
        (noted / "build").mkdir()
        (noted / "build" / "handoff.json").write_text("{}")
        self.registry.write_text(f"- record `{noted}/build/handoff.json`\n")

        proc = self.run_cli("list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        verdicts = {item["path"]: item["verdict"] for item in json.loads(proc.stdout)["items"]}
        self.assertEqual(verdicts, {str(merged): "removable", str(opened): "keep", str(deps): "removable",
                                    str(ops): "ask", str(nested): "ask", str(noted): "ask"})

    def test_remove_keeps_branch_and_refuses_open_mr(self) -> None:
        merged = self.worktree("merged", "merged")
        opened = self.worktree("opened", "opened")
        (merged / "AGENTS.md").write_text(
            "# app\n\n<!-- coding-conventions:begin general -->\nx\n<!-- coding-conventions:end general -->\n")
        (merged / "build").mkdir()
        (merged / "build" / "out.bin").write_text("x")
        (merged / "node_modules").symlink_to(self.main)
        (merged / "中文.txt").write_text("x")

        proc = self.run_cli("remove", str(merged), str(opened))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn(f"REMOVED {merged}", proc.stdout)
        self.assertIn(f"REFUSED {opened}", proc.stdout)
        self.assertFalse(merged.exists())
        self.assertTrue(opened.exists())
        self.assertTrue((self.main / "AGENTS.md").exists())
        self.assertEqual(self.git(self.main, "branch", "--list", "merged"), "merged")

    def test_without_mr_only_own_commits_already_in_the_default_branch_count_as_delivered(self) -> None:
        merged = self.worktree("merged", None)
        self.git(self.main, "merge", "-q", "--ff-only", "merged")
        drafted = self.worktree("drafted", None)
        self.git(self.main, "merge", "-q", "--ff-only", "drafted")
        (drafted / "draft.md").write_text("new work")
        pending = self.worktree("pending", None)
        pinned = self.root / "app-wt-pinned"
        self.git(self.main, "worktree", "add", "-q", "-b", "pinned", str(pinned))

        proc = self.run_cli("list", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        verdicts = {item["path"]: item["verdict"] for item in json.loads(proc.stdout)["items"]}
        self.assertEqual(verdicts, {str(merged): "removable", str(drafted): "ask",
                                    str(pending): "keep", str(pinned): "keep"})

    def test_rebased_merged_mr_requires_patch_equivalence_and_no_unique_merge(self) -> None:
        tree = self.worktree("rebased", "merged")
        old_head = self.git(tree, "rev-parse", "HEAD")
        (self.main / "upstream.txt").write_text("upstream")
        self.git(self.main, "add", ".")
        self.git(self.main, "commit", "-qm", "upstream")
        self.git(self.main, "cherry-pick", old_head)
        final = self.git(self.main, "rev-parse", "HEAD")
        mrs = json.loads(self.mrs.read_text())
        mrs["rebased"][0]["sha"] = final
        self.mrs.write_text(json.dumps(mrs))

        def item():
            proc = self.run_cli("list", "--json")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return next(i for i in json.loads(proc.stdout)["items"] if i["path"] == str(tree))

        self.assertEqual(item()["verdict"], "removable")
        self.assertEqual(item()["patch_equivalent_to"], final)
        (tree / "draft.txt").write_text("unsaved work")
        self.assertEqual(item()["verdict"], "ask")
        self.git(tree, "add", ".")
        self.git(tree, "commit", "-qm", "extra")
        self.assertEqual(item()["verdict"], "keep")
        # A merge with a novel resolution must never be hidden by git cherry.
        merge = self.git(tree, "commit-tree", "HEAD^{tree}", "-p", old_head, "-p", final, "-m", "resolution")
        self.git(tree, "reset", "--hard", merge)
        self.assertEqual(item()["verdict"], "keep")
        self.git(tree, "reset", "--hard", old_head)
        mrs["rebased"][0]["state"] = "closed"
        self.mrs.write_text(json.dumps(mrs))
        self.assertEqual(item()["verdict"], "keep")
        mrs["rebased"][0].update(state="merged", sha="a" * 40)
        self.mrs.write_text(json.dumps(mrs))
        self.assertEqual(item()["verdict"], "keep")

    def test_broad_roots_and_paths_outside_the_worktree_are_refused(self) -> None:
        proc = subprocess.run(["python3", str(SCRIPT), "remove", "--root", "/", str(self.main)],
                              capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("error[path]", proc.stderr)
        tree = self.worktree("tree", None)
        (self.tmp / "outside").mkdir()
        (tree / "link").symlink_to(self.tmp / "outside")
        for name in ("/", "", "..", "../app", "link/x"):
            with self.assertRaises(wt_sweep.SweepError, msg=name):
                wt_sweep.inside(str(tree), name)
        self.assertEqual(wt_sweep.inside(str(tree), "build/"), tree / "build")
        self.assertEqual(wt_sweep.inside(str(tree), "link"), tree / "link")


if __name__ == "__main__":
    unittest.main()
