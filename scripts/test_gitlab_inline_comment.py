from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).with_name("gitlab-mr")


def load_module():
    loader = importlib.machinery.SourceFileLoader("gitlab_mr", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class GitlabMrTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_parse_mr_url(self):
        mr = self.mod.parse_mr_url("https://gitlab.example.com/group/sub/project/-/merge_requests/123")

        self.assertEqual(mr.iid, "123")
        self.assertEqual(mr.repo, "group/sub/project")
        self.assertEqual(mr.hostname, "gitlab.example.com")

    def test_project_endpoint_uses_fullpath_placeholder_without_repo(self):
        self.assertEqual(self.mod.project_endpoint(""), "projects/:fullpath")

    def test_project_endpoint_url_encodes_repo(self):
        self.assertEqual(self.mod.project_endpoint("group/sub/project"), "projects/group%2Fsub%2Fproject")

    def test_repo_selector_carries_hostname_without_unsupported_flag(self):
        self.assertEqual(
            self.mod.repo_selector("group/project", "gitlab.example.com"),
            "https://gitlab.example.com/group/project",
        )

    def test_create_rejects_description_bypass_flags(self):
        for flag in ["--description=raw", "--fill", "--template=bug_fix", "--web"]:
            with self.subTest(flag=flag), self.assertRaisesRegex(
                    RuntimeError, "bypass"):
                self.mod.validate_create_extra_args([flag])

    def test_update_rejects_unprotected_prefix_before_licloud_tail(self):
        current = (
            "无法判定归属的正文\n\n## PR Type\n\nTests\n\n---\n\n"
            "*此描述由 Managed PR Agent PR Agent AI 自动生成*")

        with self.assertRaisesRegex(RuntimeError, "refusing to guess"):
            self.mod.compose_updated_description(current, "新内容")

    def test_create_protects_description_and_verifies_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            description_file = Path(tmp) / "description.md"
            description_file.write_text(
                "## User Description\n\n## User Description\n\n## 变更\n\n- 内容",
                encoding="utf-8",
            )
            args = SimpleNamespace(
                repo="group/project",
                hostname="gitlab.example.com",
                title="title",
                description_file=str(description_file),
                source_branch="topic",
                target_branch="master",
                label=[],
                assignee=[],
                reviewer=[],
                draft=False,
                yes=True,
                extra_args=[],
                dry_run=False,
            )
            protected = "## User Description\n\n## 变更\n\n- 内容"
            create_output = (
                "https://gitlab.example.com/group/project/-/merge_requests/12\n")
            with (
                mock.patch.object(self.mod, "run", return_value=create_output) as run,
                mock.patch.object(
                    self.mod, "glab_api",
                    return_value={"description": protected}) as api,
                redirect_stdout(io.StringIO()),
            ):
                self.mod.cmd_create(args)

        self.assertIn("--description", run.call_args.args[0])
        self.assertIn(protected, run.call_args.args[0])
        api.assert_called_once_with(
            "projects/group%2Fproject/merge_requests/12",
            hostname="gitlab.example.com",
        )

    def test_update_writes_composed_description_then_reads_it_back(self):
        tail = (
            "## PR Type\n\nEnhancement\n\n## Description\n\n- 自动摘要\n\n---\n\n"
            "*此描述由 Managed PR Agent PR Agent AI 自动生成*")
        protected = "## User Description\n\n新内容"
        expected = f"{protected}\n\n{tail}"
        with tempfile.TemporaryDirectory() as tmp:
            description_file = Path(tmp) / "description.md"
            description_file.write_text("新内容", encoding="utf-8")
            args = SimpleNamespace(
                target="12",
                repo="group/project",
                hostname="gitlab.example.com",
                description_file=str(description_file),
                dry_run=False,
            )
            with (
                mock.patch.object(
                    self.mod, "glab_api",
                    side_effect=[
                        {"description": tail},
                        {"description": tail},
                        {"description": expected},
                    ],
                ),
                mock.patch.object(self.mod, "put_mr_description") as put,
                redirect_stdout(io.StringIO()),
            ):
                self.mod.cmd_update(args)

        put.assert_called_once_with(
            "projects/group%2Fproject", "12", expected, "gitlab.example.com")

    def test_update_aborts_when_description_changes_before_write(self):
        tail = (
            "## PR Type\n\nEnhancement\n\n## Description\n\n- first\n\n---\n\n"
            "*此描述由 Managed PR Agent PR Agent AI 自动生成*")
        changed = tail.replace("- first", "- changed")
        with tempfile.TemporaryDirectory() as tmp:
            description_file = Path(tmp) / "description.md"
            description_file.write_text("新内容", encoding="utf-8")
            args = SimpleNamespace(
                target="12",
                repo="group/project",
                hostname="gitlab.example.com",
                description_file=str(description_file),
                dry_run=False,
            )
            with (
                mock.patch.object(
                    self.mod, "glab_api",
                    side_effect=[
                        {"description": tail},
                        {"description": changed},
                    ],
                ),
                mock.patch.object(self.mod, "put_mr_description") as put,
            ):
                with self.assertRaisesRegex(RuntimeError, "changed while preparing"):
                    self.mod.cmd_update(args)

        put.assert_not_called()

    def test_put_description_uses_json_input(self):
        observed = {}

        def fake_run(command):
            observed["command"] = command
            payload_path = Path(command[command.index("--input") + 1])
            observed["payload"] = json.loads(payload_path.read_text(encoding="utf-8"))
            return "{}"

        with mock.patch.object(self.mod, "run", side_effect=fake_run):
            self.mod.put_mr_description(
                "projects/group%2Fproject",
                "12",
                "## User Description\n\n内容",
                "gitlab.example.com",
            )

        self.assertEqual(
            {"description": "## User Description\n\n内容"},
            observed["payload"],
        )
        self.assertIn("Content-Type: application/json", observed["command"])

    def test_find_diff_file_accepts_old_or_new_path(self):
        diff_file = self.mod.find_diff_file(
            [{"old_path": "old/name.py", "new_path": "new/name.py"}],
            "old/name.py",
        )

        self.assertEqual(diff_file["new_path"], "new/name.py")

    def test_build_payload_uses_latest_version_position(self):
        args = SimpleNamespace(
            file="src/app.py",
            line=42,
            old_line=None,
            message="Needs a guard",
            message_file=None,
        )
        payload = self.mod.build_inline_payload(
            args,
            {"old_path": "src/app.py", "new_path": "src/app.py"},
            {
                "base_commit_sha": "base",
                "start_commit_sha": "start",
                "head_commit_sha": "head",
            },
        )

        self.assertEqual(payload["body"], "Needs a guard")
        self.assertEqual(
            payload["position"],
            {
                "position_type": "text",
                "base_sha": "base",
                "start_sha": "start",
                "head_sha": "head",
                "new_path": "src/app.py",
                "old_path": "src/app.py",
                "new_line": 42,
            },
        )

    def test_post_discussion_uses_json_input_and_content_type(self):
        observed = {}

        def fake_run(command):
            observed["command"] = command
            payload_path = Path(command[command.index("--input") + 1])
            observed["payload"] = json.loads(payload_path.read_text(encoding="utf-8"))
            return '{"id": "discussion-1"}'

        payload = {"body": "Needs a guard", "position": {"new_line": 42}}
        with mock.patch.object(self.mod, "run", side_effect=fake_run):
            result = self.mod.post_discussion(
                "projects/group%2Fproject",
                "12",
                payload,
                "gitlab.example.com",
            )

        self.assertEqual(payload, observed["payload"])
        self.assertIn("Content-Type: application/json", observed["command"])
        self.assertEqual({"id": "discussion-1"}, result)

    def test_compact_notes_omits_unneeded_api_fields(self):
        notes = self.mod.compact_notes(
            [{
                "id": "discussion-1",
                "notes": [{
                    "id": 7,
                    "author": {"username": "reviewer", "name": "Reviewer", "avatar_url": "large"},
                    "body": "Please fix this",
                    "created_at": "2026-07-28T00:00:00Z",
                    "resolvable": True,
                    "resolved": False,
                    "system": False,
                    "position": {"new_path": "src/app.py", "new_line": 42, "head_sha": "large"},
                }],
            }]
        )

        self.assertEqual(
            notes,
            [{
                "discussion_id": "discussion-1",
                "note_id": 7,
                "type": "diff",
                "resolvable": True,
                "resolved": False,
                "author": {"username": "reviewer", "name": "Reviewer"},
                "body": "Please fix this",
                "created_at": "2026-07-28T00:00:00Z",
                "position": {"new_path": "src/app.py", "new_line": 42},
            }],
        )

    def test_filter_notes_defaults_to_human_notes_and_supports_reviewer_filter(self):
        args = SimpleNamespace(
            include_system=False,
            type="all",
            state="unresolved",
            author="reviewer",
            file=None,
        )
        notes = [
            {"type": "system", "resolvable": False, "resolved": False, "author": {"username": "reviewer"}},
            {"type": "general", "resolvable": False, "resolved": False, "author": {"username": "reviewer"}},
            {"type": "diff", "resolvable": True, "resolved": False, "author": {"username": "reviewer"}},
            {"type": "diff", "resolvable": True, "resolved": False, "author": {"username": "other"}},
        ]

        self.assertEqual([notes[2]], self.mod.filter_notes(notes, args))

    def test_reviewer_add_preserves_latest_reviewers_and_verifies_readback(self):
        args = SimpleNamespace(
            target="12",
            repo="group/project",
            hostname="gitlab.example.com",
            user=["bob"],
            expected_head_sha="head-1",
            dry_run=False,
        )
        initial = {
            "sha": "head-1",
            "reviewers": [{"id": 1, "username": "alice"}],
        }
        resolved = [{"id": 2, "username": "bob", "state": "active"}]
        latest = {
            "sha": "head-1",
            "reviewers": [
                {"id": 1, "username": "alice"},
                {"id": 3, "username": "carol"},
            ],
        }
        readback = {
            "sha": "head-1",
            "reviewers": [
                {"id": 1, "username": "alice"},
                {"id": 3, "username": "carol"},
                {"id": 2, "username": "bob"},
            ],
        }
        output = io.StringIO()
        with (
            mock.patch.object(
                self.mod, "glab_api",
                side_effect=[initial, resolved, latest, readback],
            ) as api,
            mock.patch.object(self.mod, "put_mr_reviewers") as put,
            redirect_stdout(output),
        ):
            self.assertEqual(0, self.mod.cmd_reviewers_add(args))

        put.assert_called_once_with(
            "projects/group%2Fproject", "12", [1, 3, 2], "gitlab.example.com")
        self.assertEqual(
            mock.call("users?username=bob", hostname="gitlab.example.com"),
            api.call_args_list[1],
        )
        receipt = json.loads(output.getvalue())
        self.assertEqual("updated", receipt["outcome"])
        self.assertEqual(["alice", "carol"], receipt["before"])
        self.assertEqual(["bob"], receipt["added"])
        self.assertTrue(receipt["verified"])

    def test_reviewer_add_is_idempotent_without_a_second_request(self):
        args = SimpleNamespace(
            target="12",
            repo="group/project",
            hostname="gitlab.example.com",
            user=["bob", "bob"],
            expected_head_sha=None,
            dry_run=False,
        )
        current = {
            "sha": "head-1",
            "reviewers": [{"id": 2, "username": "bob"}],
        }
        output = io.StringIO()
        with (
            mock.patch.object(self.mod, "glab_api", return_value=current) as api,
            mock.patch.object(self.mod, "put_mr_reviewers") as put,
            redirect_stdout(output),
        ):
            self.assertEqual(0, self.mod.cmd_reviewers_add(args))

        api.assert_called_once()
        put.assert_not_called()
        receipt = json.loads(output.getvalue())
        self.assertEqual("already_present", receipt["outcome"])
        self.assertEqual(["bob"], receipt["requested"])
        self.assertTrue(receipt["verified"])

    def test_reviewer_add_stops_before_write_on_head_change(self):
        args = SimpleNamespace(
            target="12",
            repo="group/project",
            hostname="gitlab.example.com",
            user=["bob"],
            expected_head_sha="head-1",
            dry_run=False,
        )
        with (
            mock.patch.object(
                self.mod, "glab_api",
                side_effect=[
                    {"sha": "head-1", "reviewers": []},
                    [{"id": 2, "username": "bob", "state": "active"}],
                    {"sha": "head-2", "reviewers": []},
                ],
            ),
            mock.patch.object(self.mod, "put_mr_reviewers") as put,
        ):
            with self.assertRaises(self.mod.ReviewerOperationError) as raised:
                self.mod.cmd_reviewers_add(args)

        self.assertEqual("not_applied", raised.exception.outcome)
        put.assert_not_called()

    def test_reviewer_add_marks_unverified_readback_ambiguous(self):
        args = SimpleNamespace(
            target="12",
            repo="group/project",
            hostname="gitlab.example.com",
            user=["bob"],
            expected_head_sha=None,
            dry_run=False,
        )
        with (
            mock.patch.object(
                self.mod, "glab_api",
                side_effect=[
                    {"sha": "head-1", "reviewers": []},
                    [{"id": 2, "username": "bob", "state": "active"}],
                    {"sha": "head-1", "reviewers": []},
                    {"sha": "head-1", "reviewers": []},
                ],
            ),
            mock.patch.object(self.mod, "put_mr_reviewers"),
        ):
            with self.assertRaises(self.mod.ReviewerOperationError) as raised:
                self.mod.cmd_reviewers_add(args)

        self.assertEqual("ambiguous", raised.exception.outcome)

    def test_put_reviewers_uses_json_array_and_content_type(self):
        observed = {}

        def fake_run(command):
            observed["command"] = command
            payload_path = Path(command[command.index("--input") + 1])
            observed["payload"] = json.loads(payload_path.read_text(encoding="utf-8"))
            return "{}"

        with mock.patch.object(self.mod, "run", side_effect=fake_run):
            self.mod.put_mr_reviewers(
                "projects/group%2Fproject", "12", [1, 3, 2], "gitlab.example.com")

        self.assertEqual({"reviewer_ids": [1, 3, 2]}, observed["payload"])
        self.assertIn("Content-Type: application/json", observed["command"])


if __name__ == "__main__":
    unittest.main()
