import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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
        dry_run: bool = False,
        remote_dry_run: bool = False,
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

    def test_healthy_refresh_runs_only_once_per_local_day(self) -> None:
        first = self.run_refresh()

        (self.writer / "README.md").write_text("three\n")
        git(self.writer, "add", "README.md")
        git(self.writer, "commit", "-m", "another remote update")
        git(self.writer, "push")
        newer_remote_head = git(self.writer, "rev-parse", "HEAD")
        self.assertNotEqual(newer_remote_head, self.remote_head)

        second = self.run_refresh(force=False, once_per_day=True)
        self.assertEqual(second["checked_at"], first["checked_at"])
        self.assertEqual(git(self.clean, "rev-parse", "HEAD"), self.remote_head)

    def test_parses_gitlab_ssh_and_https_remotes(self) -> None:
        expected = self.mod.GitLabRemote("gitlab.example.com", "group/demo")
        self.assertEqual(
            self.mod.parse_gitlab_remote("git@gitlab.example.com:group/demo.git"),
            expected,
        )
        self.assertEqual(
            self.mod.parse_gitlab_remote("https://gitlab.example.com/group/demo.git"),
            expected,
        )
        self.assertIsNone(self.mod.parse_gitlab_remote(str(self.remote)))

    def test_broker_json_returns_data_from_gtd_bridge(self) -> None:
        original_run_gtd_broker = self.mod.run_gtd_broker

        def fake_run_gtd_broker(request, _timeout_seconds):
            self.assertEqual(request["resource"], "mr-list")
            return subprocess.CompletedProcess(
                ["gtd"],
                0,
                '{"ok":true,"data":[{"iid":1},{"iid":2}]}',
                "",
            )

        self.mod.run_gtd_broker = fake_run_gtd_broker
        try:
            payload = self.mod.broker_json(
                "mr-list",
                "gitlab.example.com",
                30,
                project="group/demo",
                query={
                    "scope": "all",
                    "state": "all",
                    "source_branch": "feat/test",
                    "per_page": "100",
                },
            )
        finally:
            self.mod.run_gtd_broker = original_run_gtd_broker

        self.assertEqual(payload, [{"iid": 1}, {"iid": 2}])

    def test_gtd_broker_uses_explicit_node_command(self) -> None:
        completed = subprocess.CompletedProcess(["node", "gtd"], 0, "{}", "")

        with (
            mock.patch.dict(
                self.mod.os.environ,
                {
                    "AMT_GTD_COMMAND": "/runtime/gtd",
                    "AMT_GTD_NODE": "/runtime/node",
                },
            ),
            mock.patch.object(
                self.mod.subprocess,
                "run",
                return_value=completed,
            ) as run,
        ):
            self.mod.run_gtd_broker({"resource": "mr-list"}, 30)

        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/runtime/node", "/runtime/gtd"])
        self.assertEqual(command[2:6], ["gitlab", "broker", "request", "--json"])

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

    def test_cleanup_deletes_verified_squash_merged_branches(self) -> None:
        branch = "feat-clean"
        feature_sha = self.create_feature_branch(branch)

        report, delete_calls, broker_requests = self.cleanup_feature(
            [self.merged_mr(branch, feature_sha)]
        )

        self.assertEqual(
            report["deleted_local_branches"],
            [{"branch": branch, "mr_iid": 12}],
        )
        self.assertEqual(
            report["deleted_remote_branches"],
            [{"branch": branch, "mr_iid": 12}],
        )
        self.assertEqual(git(self.clean, "branch", "--list", branch), "")
        tracking_ref = subprocess.run(
            [
                "git",
                "-C",
                str(self.clean),
                "show-ref",
                "--verify",
                f"refs/remotes/origin/{branch}",
            ],
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(tracking_ref.returncode, 0)
        self.assertEqual(len(delete_calls), 1)
        self.assertIn("DELETE", delete_calls[0])
        mr_requests = [
            request for request in broker_requests
            if request["resource"] == "mr-list"
        ]
        self.assertEqual(len(mr_requests), 1)
        self.assertEqual(
            mr_requests[0]["query"],
            {
                "scope": "all",
                "state": "all",
                "source_branch": branch,
                "per_page": "100",
            },
        )

    def test_cleanup_without_topic_candidates_does_not_query_gitlab(self) -> None:
        report, delete_calls, broker_requests = self.cleanup_feature([])

        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["broker_requests"], 0)
        self.assertEqual(broker_requests, [])
        self.assertEqual(delete_calls, [])

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
        self.assertTrue(branch_report["eligible"])
        self.assertEqual(branch_report["action"], "dry_run")
        self.assertEqual(git(self.clean, "branch", "--list", branch), branch)
        self.assertEqual(
            git(self.clean, "rev-parse", f"origin/{branch}"),
            feature_sha,
        )
        self.assertEqual(delete_calls, [])

    def test_remote_dry_run_deletes_local_and_preserves_remote_branch(self) -> None:
        branch = "feat-remote-dry-run"
        feature_sha = self.create_feature_branch(branch)

        report, delete_calls, _broker_requests = self.cleanup_feature(
            [self.merged_mr(branch, feature_sha)],
            remote_dry_run=True,
        )

        self.assertEqual(
            report["deleted_local_branches"],
            [{"branch": branch, "mr_iid": 12}],
        )
        self.assertEqual(
            report["remote_dry_run_branches"],
            [{"branch": branch, "mr_iid": 12}],
        )
        self.assertEqual(report["deleted_remote_branches"], [])
        self.assertEqual(git(self.clean, "branch", "--list", branch), "")
        self.assertEqual(
            git(self.clean, "rev-parse", f"origin/{branch}"),
            feature_sha,
        )
        self.assertEqual(delete_calls, [])


if __name__ == "__main__":
    unittest.main()
