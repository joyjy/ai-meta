from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).with_name("gitlab-project-lint")


def load_module():
    loader = importlib.machinery.SourceFileLoader("gitlab_project_lint",
                                                  str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class GitlabProjectLintTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        self.original_run = self.mod.run
        self.original_glab_json = self.mod.glab_json

    def tearDown(self):
        self.mod.run = self.original_run
        self.mod.glab_json = self.original_glab_json

    def test_repo_from_remote_accepts_ssh_and_https(self):
        self.assertEqual(
            self.mod.repo_from_remote(
                "git@gitlab.example.com:example-org/demo/service.git"),
            "example-org/demo/service",
        )
        self.assertEqual(
            self.mod.repo_from_remote(
                "https://gitlab.example.com/example-org/demo/service.git"),
            "example-org/demo/service",
        )

    def test_frontmatter_reads_inline_gitlab_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text(
                '---\ngitlab: {flow: l2, squash: default-on, lint: "PASS@2026-07-10"}\n---\n',
                encoding="utf-8")

            self.assertEqual(self.mod.gitlab_config_from_index(path),
                             ("l2", "default-on"))

    def test_frontmatter_reads_repo_inline_gitlab_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            path = Path(tmp) / "index.md"
            path.write_text(
                f'---\nrepos:\n  - path: {repo}\n    gitlab: {{flow: l1, squash: required, lint: "PASS@2026-07-10"}}\n---\n',
                encoding="utf-8",
            )

            self.assertEqual(
                self.mod.gitlab_config_for_repo(path, repo,
                                                "example-org/demo/service"),
                ("l1", "required"))

    def test_resolve_only_reports_worktree_canonical_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            worktree = root / "repo-feature"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.name=Test",
                 "-c", "user.email=test@example.com", "commit",
                 "--allow-empty", "-qm", "init"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "-qb",
                 "feature", str(worktree)],
                check=True,
            )
            path = root / "index.md"
            path.write_text(
                f'---\nrepos:\n  - path: {repo}\n    gitlab: {{flow: l2, squash: default-on}}\n---\n',
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    self.mod.main([
                        "--cwd", str(worktree), "--index", str(path),
                        "--repo", "example-org/demo/service", "--resolve-only",
                        "--json"
                    ]),
                    0,
                )

            resolution = json.loads(output.getvalue())
            self.assertEqual(resolution["matched_path"], str(repo))
            self.assertEqual(resolution["gitlab"]["flow"], "l2")

            self.assertTrue(
                self.mod.upsert_repo_gitlab_result(
                    path,
                    worktree,
                    "example-org/demo/service",
                    {"lint": "PASS@2026-07-14"},
                ))
            self.assertIn(
                'gitlab: {flow: l2, squash: default-on, lint: "PASS@2026-07-14"}',
                path.read_text(encoding="utf-8"),
            )

    def test_write_lint_result_preserves_gitlab_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text(
                "---\nabbr: demo\ngitlab: {flow: l2, squash: required}\n---\n# Demo\n",
                encoding="utf-8")

            self.mod.write_lint_result(path, "example-org/demo/service", "OK", [])
            data = self.mod.frontmatter(path)

            self.assertEqual(data["abbr"], "demo")
            self.assertEqual(data["gitlab"]["flow"], "l2")
            self.assertEqual(data["gitlab"]["squash"], "required")
            self.assertRegex(data["gitlab"]["lint"], r"OK@\d{4}-\d{2}-\d{2}")
            self.assertIn("# Demo", path.read_text(encoding="utf-8"))

    def test_write_lint_result_updates_matching_repo_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            other = Path(tmp) / "other"
            repo.mkdir()
            other.mkdir()
            path = Path(tmp) / "index.md"
            path.write_text(
                f"---\nabbr: demo\nrepos:\n  - path: {repo}\n    gitlab: {{flow: l2, squash: required}}\n  - path: {other}\n    gitlab: {{flow: l3}}\n---\n# Demo\n",
                encoding="utf-8",
            )

            changed = self.mod.upsert_repo_gitlab_result(
                path, repo, "example-org/demo/service", {
                    "lint": "PASS@2026-07-10",
                })

            self.assertTrue(changed)
            text = path.read_text(encoding="utf-8")
            self.assertRegex(
                text,
                r'gitlab: \{flow: l2, squash: required, lint: "PASS@\d{4}-\d{2}-\d{2}"\}'
            )
            self.assertEqual(text.count("lint:"), 1)
            self.assertIn(f"  - path: {other}\n    gitlab: {{flow: l3}}", text)

    def test_write_lint_result_refuses_project_fallback_when_repos_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            other = Path(tmp) / "other"
            repo.mkdir()
            other.mkdir()
            path = Path(tmp) / "index.md"
            path.write_text(
                f"---\nabbr: demo\nrepos:\n  - path: {other}\n    gitlab: {{flow: l3}}\n---\n# Demo\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "No matching repos"):
                self.mod.write_lint_values(path, repo, "example-org/demo/service",
                                           "PASS", [])

    def test_check_project_respects_squash_policy(self):
        common = {
            "merge_method": "ff",
            "only_allow_merge_if_pipeline_succeeds": True,
            "allow_merge_on_skipped_pipeline": False,
            "remove_source_branch_after_merge": True,
            "only_allow_merge_if_all_discussions_are_resolved": True,
        }

        self.assertEqual(
            self.mod.check_project({
                **common, "squash_option": "always"
            }, "required"), [])
        self.assertEqual(
            self.mod.check_project({
                **common, "squash_option": "default_on"
            }, "required"), [])
        self.assertEqual(
            self.mod.check_project({
                **common, "squash_option": "always"
            }, "default-on"), [])
        self.assertEqual(
            self.mod.check_project({
                **common, "squash_option": "default_off"
            }, "default-off"), [])
        self.assertEqual(
            self.mod.check_project({
                **common, "squash_option": "default_off"
            }, "required")[0].field,
            "squash_option",
        )

    def test_checks_full_gitlab_settings_baseline(self):
        project = {
            "default_branch": "main",
            "merge_method": "ff",
            "squash_option": "default_on",
            "only_allow_merge_if_pipeline_succeeds": True,
            "allow_merge_on_skipped_pipeline": False,
            "remove_source_branch_after_merge": True,
            "only_allow_merge_if_all_discussions_are_resolved": True,
        }
        approvals = {
            "approvals_before_merge": 0,
            "reset_approvals_on_push": True,
            "disable_overriding_approvers_per_merge_request": True,
            "merge_requests_author_approval": False,
            "merge_requests_disable_committers_approval": False,
            "require_password_to_approve": False,
            "require_reauthentication_to_approve": False,
        }
        rules = [{
            "name": "All Members",
            "rule_type": "any_approver",
            "approvals_required": 1,
            "applies_to_all_protected_branches": False,
        }]
        push_rule = {
            "branch_name_regex": "^(epic|feat|fix|test|doc|proposal)-",
        }
        protected_branches = [{
            "name": "main",
            "merge_access_levels": [{
                "access_level": 30
            }],
            "push_access_levels": [{
                "access_level": 0
            }],
        }]

        self.assertEqual(self.mod.check_project(project, "default-on"), [])
        self.assertEqual(self.mod.check_approvals(approvals), [])
        self.assertEqual(self.mod.check_approval_rules(rules), [])
        self.assertEqual(self.mod.check_push_rule(push_rule), [])
        self.assertEqual(
            self.mod.check_protected_branches(project, protected_branches), [])

    def test_branch_name_push_rule_drift_is_reported(self):
        expected = "^(epic|feat|fix|test|doc|proposal)-"

        for push_rule, actual in ((None, None), ({"branch_name_regex": ""}, "")):
            with self.subTest(push_rule=push_rule):
                findings = self.mod.check_push_rule(push_rule)
                self.assertEqual(
                    [(finding.area, finding.field, finding.actual,
                      finding.expected) for finding in findings],
                    [("push_rule", "branch_name_regex", actual, expected)],
                )

    def test_protected_branch_drift_is_reported(self):
        findings = self.mod.check_protected_branches(
            {"default_branch": "main"},
            [{
                "name": "main",
                "merge_access_levels": [{
                    "access_level": 40
                }],
                "push_access_levels": [{
                    "access_level": 30
                }],
            }],
        )

        self.assertEqual(
            [(finding.area, finding.field, finding.actual, finding.expected)
             for finding in findings],
            [
                ("protected_branches", "main.merge_access_level", "40", 30),
                ("protected_branches", "main.push_access_level", "30", 0),
            ],
        )


    def test_global_user_push_exceptions_are_allowed(self):
        findings = self.mod.check_protected_branches(
            {"default_branch": "main"},
            [{
                "name": "main",
                "merge_access_levels": [{
                    "access_level": 30
                }],
                "push_access_levels": [{
                    "access_level": 40,
                    "user_id": 1,
                    "access_level_description": "Pro-CI-Bot",
                }, {
                    "access_level": 40,
                    "user_id": 2,
                    "access_level_description": "Arch-CICD-Worker",
                }],
            }],
        )

        self.assertEqual(findings, [])

    def test_unconfigured_user_push_exception_is_reported_by_name(self):
        findings = self.mod.check_protected_branches(
            {"default_branch": "main"},
            [{
                "name": "main",
                "merge_access_levels": [{
                    "access_level": 30
                }],
                "push_access_levels": [{
                    "access_level": 40,
                    "user_id": 1,
                    "access_level_description": "Other-Bot",
                }],
            }],
        )

        self.assertEqual(
            [(finding.area, finding.field, finding.actual, finding.expected)
             for finding in findings],
            [("protected_branches", "main.push_access_level", "Other-Bot", 0)],
        )

    def test_l1_l2_reject_non_baseline_squash_metadata(self):
        self.mod.run = lambda _cmd: "git@gitlab.example.com:example-org/demo/service.git"
        self.mod.glab_json = lambda _endpoint, _hostname="": self.fail(
            "glab_json should not be called")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text("---\ngitlab: {flow: l2, squash: disabled}\n---\n",
                            encoding="utf-8")

            with self.assertRaisesRegex(
                    RuntimeError, "Unsupported GitLab squash policy for l2"):
                self.mod.main(["--cwd", tmp, "--index", str(path)])

    def test_l1_l2_missing_squash_defaults_to_default_on_and_writes_index(self):
        self.mod.run = lambda _cmd: "git@gitlab.example.com:example-org/demo/service.git"

        def glab_json(endpoint, _hostname=""):
            if endpoint.endswith("/approvals"):
                return {
                    "approvals_before_merge": 0,
                    "reset_approvals_on_push": True,
                    "disable_overriding_approvers_per_merge_request": True,
                    "merge_requests_author_approval": False,
                    "merge_requests_disable_committers_approval": False,
                    "require_password_to_approve": False,
                    "require_reauthentication_to_approve": False,
                }
            if endpoint.endswith("/approval_rules"):
                return [{
                    "name": "All Members",
                    "rule_type": "any_approver",
                    "approvals_required": 1,
                    "applies_to_all_protected_branches": False,
                }]
            if endpoint.endswith("/push_rule"):
                return {
                    "branch_name_regex":
                    "^(epic|feat|fix|test|doc|proposal)-",
                }
            if endpoint.endswith("/protected_branches"):
                return [{
                    "name": "main",
                    "merge_access_levels": [{
                        "access_level": 30
                    }],
                    "push_access_levels": [{
                        "access_level": 0
                    }],
                }]
            return {
                "default_branch": "main",
                "merge_method": "ff",
                "only_allow_merge_if_pipeline_succeeds": True,
                "allow_merge_on_skipped_pipeline": False,
                "remove_source_branch_after_merge": True,
                "only_allow_merge_if_all_discussions_are_resolved": True,
                "squash_option": "default_on",
            }

        self.mod.glab_json = glab_json

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            path = Path(tmp) / "index.md"
            path.write_text(
                f"---\nrepos:\n  - path: {repo}\n    gitlab: {{flow: l2}}\n---\n# Demo\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    self.mod.main([
                        "--cwd",
                        str(repo), "--index",
                        str(path), "--write-index"
                    ]),
                    0,
                )

            text = path.read_text(encoding="utf-8")
            self.assertIn("squash: default-on", text)
            self.assertRegex(text, r'lint: "PASS@\d{4}-\d{2}-\d{2}"')
            self.assertIn("- squash: `default-on`", output.getvalue())

    def test_l3_flow_skips_gitlab_api(self):
        self.mod.run = lambda _cmd: "git@gitlab.example.com:example-org/demo/service.git"
        self.mod.glab_json = lambda _endpoint, _hostname="": self.fail(
            "glab_json should not be called")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text("---\ngitlab: {flow: l3}\n---\n",
                            encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    self.mod.main(["--cwd", tmp, "--index",
                                   str(path)]), 0)
            self.assertIn("status: SKIP", output.getvalue())


if __name__ == "__main__":
    unittest.main()
