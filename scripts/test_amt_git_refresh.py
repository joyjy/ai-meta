import importlib.machinery
import importlib.util
import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/amt-git-refresh"


def load_module():
    loader = importlib.machinery.SourceFileLoader("amt_git_refresh", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr or result.stdout}")
    return result.stdout.strip()


class AmtGitRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.remote = self.root / "remote.git"
        self.writer = self.root / "writer"
        self.clean = self.root / "clean"
        self.dirty = self.root / "dirty"
        self.parent = self.root / "parent"
        self.output = self.root / "report.json"

        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.writer)], check=True, capture_output=True)
        git(self.writer, "config", "user.name", "Test")
        git(self.writer, "config", "user.email", "test@example.com")
        (self.writer / "README.md").write_text("one\n")
        git(self.writer, "add", "README.md")
        git(self.writer, "commit", "-m", "initial")
        git(self.writer, "branch", "-M", "main")
        git(self.writer, "push", "-u", "origin", "main")
        git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")

        subprocess.run(["git", "init", str(self.parent)], check=True, capture_output=True)
        git(self.parent, "config", "user.name", "Test")
        git(self.parent, "config", "user.email", "test@example.com")
        git(
            self.parent,
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            str(self.remote),
            "external/sdk",
        )
        git(self.parent, "commit", "-m", "add submodule")

        subprocess.run(["git", "clone", str(self.remote), str(self.clean)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.dirty)], check=True, capture_output=True)
        git(self.clean, "config", "user.name", "Test")
        git(self.clean, "config", "user.email", "test@example.com")
        git(self.clean, "switch", "-c", "work")
        git(self.clean, "branch", "--set-upstream-to", "origin/main", "work")
        self.before = git(self.clean, "rev-parse", "HEAD")

        (self.writer / "README.md").write_text("two\n")
        git(self.writer, "add", "README.md")
        git(self.writer, "commit", "-m", "remote update")
        git(self.writer, "push")
        self.remote_head = git(self.writer, "rev-parse", "HEAD")
        (self.dirty / "local.txt").write_text("keep me\n")

    def create_feature_branch(self, branch: str = "feat-clean") -> str:
        git(self.writer, "switch", "-c", branch)
        (self.writer / "feature.txt").write_text(f"{branch}\n")
        git(self.writer, "add", "feature.txt")
        git(self.writer, "commit", "-m", branch)
        git(self.writer, "push", "-u", "origin", branch)
        feature_sha = git(self.writer, "rev-parse", "HEAD")
        git(self.clean, "fetch", "origin")
        git(self.clean, "branch", branch, f"origin/{branch}")
        return feature_sha

    def merged_mr(self, branch: str, sha: str, *, iid: int = 12) -> dict:
        return {
            "iid": iid,
            "state": "merged",
            "source_branch": branch,
            "target_branch": "main",
            "source_project_id": 7,
            "target_project_id": 7,
            "sha": sha,
            "squash": True,
            "squash_commit_sha": "f" * 40,
            "merged_at": "2026-07-24T01:00:00Z",
            "web_url": f"https://gitlab.example.com/group/demo/-/merge_requests/{iid}",
            "references": {"full": f"group/demo!{iid}"},
        }

    def cleanup_feature(
        self,
        merge_requests: list[dict],
        *,
        dry_run: bool = True,
        remote_dry_run: bool = True,
    ) -> tuple[dict, list[list[str]], list[dict]]:
        original_broker_json = self.mod.broker_json
        original_run_glab = self.mod.run_glab
        delete_calls: list[list[str]] = []
        broker_requests: list[dict] = []

        def fake_broker_json(resource, _hostname, _timeout_seconds, **kwargs):
            broker_requests.append({"resource": resource, **kwargs})
            if resource == "mr-list":
                return merge_requests
            return {"default": False, "protected": False}

        def fake_run_glab(args, _timeout_seconds):
            delete_calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        self.mod.broker_json = fake_broker_json
        self.mod.run_glab = fake_run_glab
        try:
            report = self.mod.cleanup_repository_branches(
                self.clean,
                self.mod.GitLabRemote("gitlab.example.com", "group/demo"),
                30,
                dry_run=dry_run,
                remote_dry_run=remote_dry_run,
            )
        finally:
            self.mod.broker_json = original_broker_json
            self.mod.run_glab = original_run_glab
        return report, delete_calls, broker_requests

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_refresh(
        self,
        *,
        force: bool = True,
        once_per_day: bool = False,
        excludes: tuple[Path, ...] = (),
    ) -> dict:
        args = [
            str(SCRIPT),
            "--root",
            str(self.root),
            "--output",
            str(self.output),
        ]
        if force:
            args.append("--force")
        if once_per_day:
            args.append("--once-per-day")
        for excluded in excludes:
            args.extend(["--exclude", str(excluded)])
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(self.output.read_text())

    def test_fetches_all_and_only_fast_forwards_clean_tracked_branch(self) -> None:
        report = self.run_refresh()

        self.assertEqual(git(self.clean, "rev-parse", "HEAD"), self.remote_head)
        self.assertEqual(git(self.clean, "branch", "--show-current"), "work")
        self.assertEqual(git(self.dirty, "rev-parse", "HEAD"), self.before)
        self.assertEqual(git(self.dirty, "rev-parse", "origin/main"), self.remote_head)
        self.assertTrue((self.dirty / "local.txt").exists())

        by_path = {item["path"]: item for item in report["repositories"]}
        self.assertEqual(by_path[str(self.clean)]["status"], "fast_forwarded")
        self.assertEqual(by_path[str(self.dirty)]["status"], "skipped_dirty")
        self.assertNotIn(str(self.parent / "external/sdk"), by_path)
        self.assertEqual(
            report["ignored_submodules"],
            [{"path": str(self.parent / "external/sdk"), "superproject": str(self.parent)}],
        )
        self.assertEqual(report["state"], "healthy")

    def test_one_repository_failure_does_not_stop_later_repositories(self) -> None:
        git(self.clean, "remote", "set-url", "origin", str(self.root / "missing.git"))
        report = self.run_refresh()

        by_path = {item["path"]: item for item in report["repositories"]}
        self.assertEqual(by_path[str(self.clean)]["status"], "fetch_failed")
        self.assertEqual(by_path[str(self.dirty)]["status"], "skipped_dirty")
        self.assertEqual(git(self.dirty, "rev-parse", "origin/main"), self.remote_head)
        self.assertEqual(report["state"], "degraded")

    def test_excluded_repository_is_reported_without_fetching(self) -> None:
        git(self.clean, "remote", "set-url", "origin", str(self.root / "missing.git"))

        report = self.run_refresh(excludes=(self.clean,))

        by_path = {item["path"]: item for item in report["repositories"]}
        self.assertNotIn(str(self.clean), by_path)
        self.assertEqual(report["excluded_paths"], [str(self.clean)])
        self.assertEqual(report["excluded_repositories"], [{"path": str(self.clean)}])
        self.assertEqual(git(self.clean, "rev-parse", "HEAD"), self.before)
        self.assertEqual(report["state"], "healthy")

    def test_cleanup_excludes_configured_project_prefix(self) -> None:
        original_gitlab_remote = self.mod.gitlab_remote
        original_cleanup_repository_branches = self.mod.cleanup_repository_branches

        def fail_cleanup(*_args, **_kwargs):
            raise AssertionError("excluded project must not enter branch cleanup")

        self.mod.gitlab_remote = lambda _repo, _timeout: self.mod.GitLabRemote(
            "gitlab.example.com",
            "example-org/3rd/growthbook",
        )
        self.mod.cleanup_repository_branches = fail_cleanup
        try:
            report = self.mod.cleanup_merged_branches(
                [self.clean],
                [],
                30,
                dry_run=True,
                excluded_project_prefixes=("example-org/3rd/",),
            )
        finally:
            self.mod.gitlab_remote = original_gitlab_remote
            self.mod.cleanup_repository_branches = original_cleanup_repository_branches

        self.assertEqual(report["counts"]["repositories"], 0)
        self.assertEqual(report["counts"]["excluded_repositories"], 1)
        self.assertEqual(
            report["excluded_repositories"],
            [
                {
                    "path": str(self.clean),
                    "project": "example-org/3rd/growthbook",
                    "reason": "project_prefix",
                    "prefix": "example-org/3rd/",
                }
            ],
        )

    def test_cleanup_verifies_squash_mr_without_deleting_refs(self) -> None:
        branch = "feat-clean"
        feature_sha = self.create_feature_branch(branch)
        report, delete_calls, broker_requests = self.cleanup_feature([self.merged_mr(branch, feature_sha)])
        self.assertEqual(report["deleted_local_branches"], [])
        self.assertEqual(report["deleted_remote_branches"], [])
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(delete_calls, [])
        mr_requests = [request for request in broker_requests if request["resource"] == "mr-list"]
        self.assertEqual(len(mr_requests), 1)
        self.assertEqual(mr_requests[0]["query"]["source_branch"], branch)
        self.assertEqual(next(x for x in report["branches"] if x["branch"] == branch)["mr_iid"], 12)

    def test_cleanup_skips_branch_with_open_mr(self) -> None:
        branch = "feat-open"
        feature_sha = self.create_feature_branch(branch)
        merged = self.merged_mr(branch, feature_sha)
        opened = merged | {"iid": 13, "state": "opened"}

        report, delete_calls, _broker_requests = self.cleanup_feature(
            [merged, opened]
        )

        self.assertEqual(report["deleted_local_branches"], [])
        self.assertEqual(report["deleted_remote_branches"], [])
        branch_report = next(
            item for item in report["branches"] if item["branch"] == branch
        )
        self.assertEqual(branch_report["reason"], "open_mr_exists")
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(delete_calls, [])

    def test_cleanup_ignores_non_squash_merge(self) -> None:
        branch = "feat-merge-commit"
        feature_sha = self.create_feature_branch(branch)
        merged = self.merged_mr(branch, feature_sha) | {
            "squash": False,
            "squash_commit_sha": None,
        }

        report, delete_calls, _broker_requests = self.cleanup_feature([merged])

        self.assertEqual(report["candidates"], [])
        branch_report = next(
            item for item in report["branches"] if item["branch"] == branch
        )
        self.assertEqual(branch_report["reason"], "no_squash_merged_mr")
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(delete_calls, [])

    def test_cleanup_skips_branch_with_post_merge_remote_commit(self) -> None:
        branch = "feat-advanced"
        merged_source_sha = self.create_feature_branch(branch)
        (self.writer / "feature.txt").write_text("advanced\n")
        git(self.writer, "add", "feature.txt")
        git(self.writer, "commit", "-m", "post merge work")
        git(self.writer, "push")
        git(self.clean, "fetch", "origin")

        report, delete_calls, _broker_requests = self.cleanup_feature(
            [self.merged_mr(branch, merged_source_sha)]
        )

        branch_report = next(
            item for item in report["branches"] if item["branch"] == branch
        )
        self.assertEqual(
            branch_report["reason"], "remote_branch_has_post_merge_commits"
        )
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(delete_calls, [])

    def test_cleanup_dry_run_reports_without_deleting(self) -> None:
        branch = "feat-dry-run"
        feature_sha = self.create_feature_branch(branch)

        report, delete_calls, _broker_requests = self.cleanup_feature(
            [self.merged_mr(branch, feature_sha)],
            dry_run=True,
        )

        branch_report = next(
            item for item in report["branches"] if item["branch"] == branch
        )
        self.assertFalse(branch_report["eligible"])
        self.assertEqual(branch_report["classification"], "unique_content")
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(
            git(self.clean, "rev-parse", f"origin/{branch}"),
            feature_sha,
        )
        self.assertEqual(delete_calls, [])

    def review_args(self, report, *, confirm=False):
        review = self.mod.review_docs.build_review({"repositories": [report]}, {"items": []}, None)
        plan = self.root / "review.json"
        plan.write_text(json.dumps({"review": review}))
        entry = next(e for e in review["entries"] if e["branch"].startswith("feat-"))
        return argparse.Namespace(apply_review=plan, select=[entry["entry_id"]], scope="both",
                                  confirm=confirm, discard_unmerged=False,
                                  timeout_seconds=30, output=self.root / "apply.json")

    def fresh_api(self, _remote, endpoint, _timeout):
        if "merge_requests?" in endpoint:
            return []
        if "/repository/branches/" in endpoint:
            branch = endpoint.rsplit("/", 1)[1]
            return {"protected": False, "default": False,
                    "commit": {"id": git(self.remote, "rev-parse", f"refs/heads/{branch}")}}
        return {"default_branch": "main"}

    def test_review_preview_and_selected_deletion_use_real_git_refs(self) -> None:
        branch = "feat-reviewed"
        self.create_feature_branch(branch)
        git(self.writer, "switch", "main")
        git(self.writer, "merge", "--ff-only", branch)
        git(self.writer, "push", "origin", "main")
        git(self.clean, "fetch", "origin")
        report, _, _ = self.cleanup_feature([], dry_run=True)
        entry = next(e for e in report["branches"] if e["branch"] == branch)
        self.assertEqual(entry["classification"], "redundant")
        args = self.review_args(report)
        remote = self.mod.GitLabRemote("gitlab.example.com", "group/demo")
        with patch.object(self.mod, "gitlab_remote", return_value=remote), \
             patch.object(self.mod, "parse_gitlab_remote", return_value=remote), \
             patch.object(self.mod, "fresh_gitlab_json", side_effect=self.fresh_api), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.apply_review(args), 0)
            self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
            self.assertTrue(git(self.remote, "branch", "--list", branch))
            args.confirm = True
            self.assertEqual(self.mod.apply_review(args), 0)
        self.assertEqual(git(self.clean, "branch", "--list", branch), "")
        self.assertEqual(git(self.remote, "branch", "--list", branch), "")
        self.assertTrue(git(self.remote, "branch", "--list", "main"))
        self.assertEqual(git(self.clean, "branch", "--show-current"), "work")

    def test_unique_content_requires_approval_and_stale_snapshot_is_refused(self) -> None:
        branch = "feat-unique"
        self.create_feature_branch(branch)
        report, _, _ = self.cleanup_feature([], dry_run=True)
        item = next(e for e in report["branches"] if e["branch"] == branch)
        self.assertEqual(item["classification"], "unique_content")
        self.assertEqual(item["evidence"][0]["changed_files"], ["feature.txt"])
        args = self.review_args(report, confirm=True)
        with self.assertRaisesRegex(ValueError, "discard-unmerged"):
            self.mod.apply_review(args)
        args.discard_unmerged = True
        git(self.clean, "update-ref", f"refs/heads/{branch}", self.remote_head)
        remote = self.mod.GitLabRemote("gitlab.example.com", "group/demo")
        with patch.object(self.mod, "gitlab_remote", return_value=remote), \
             patch.object(self.mod, "parse_gitlab_remote", return_value=remote):
            with self.assertRaisesRegex(ValueError, "local_sha changed"):
                self.mod.apply_review(args)
        self.assertTrue(git(self.remote, "branch", "--list", branch))

    def test_remote_delete_lease_rejects_tip_changed_after_preflight(self) -> None:
        branch = "feat-race"
        old = self.create_feature_branch(branch)
        report, _, _ = self.cleanup_feature([], dry_run=True)
        args = self.review_args(report, confirm=True)
        args.scope, args.discard_unmerged = "remote", True
        (self.writer / "feature.txt").write_text("new work\n")
        git(self.writer, "add", "feature.txt")
        git(self.writer, "commit", "-m", "new work after scan")
        new = git(self.writer, "rev-parse", "HEAD")
        original = self.mod.run_git
        def raced(repo, command, timeout):
            if command[0] == "push":
                git(self.writer, "push", "origin", branch)
            return original(repo, command, timeout)
        remote = self.mod.GitLabRemote("gitlab.example.com", "group/demo")
        with patch.object(self.mod, "gitlab_remote", return_value=remote), \
             patch.object(self.mod, "parse_gitlab_remote", return_value=remote), \
             patch.object(self.mod, "fresh_gitlab_json", side_effect=self.fresh_api), \
             patch.object(self.mod, "run_git", side_effect=raced), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.apply_review(args), 1)
        self.assertNotEqual(old, new)
        self.assertEqual(git(self.remote, "rev-parse", f"refs/heads/{branch}"), new)


if __name__ == "__main__":
    unittest.main()
