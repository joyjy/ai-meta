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

from ll_contract_file import load_path, render_hot_block

SCRIPT = Path(__file__).with_name("verify-ll-contract")
LEDGER = Path(__file__).with_name("ll-ledger")
FIXTURES = Path(__file__).with_name("fixtures") / "ll-contracts"


def load_module():
    loader = importlib.machinery.SourceFileLoader("verify_ll_contract",
                                                  str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class VerifyLLContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def run_contract(self, path: Path) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = self.mod.main([str(path)])
        return code, output.getvalue()

    def test_golden_contracts_pass(self):
        for name in [
                "base_ll_contract.json",
                "engineering_exit_manual_report.json",
                "engineering_exit_codex_goal.json",
                "engineering_exit_blocker_report.json",
        ]:
            with self.subTest(name=name):
                code, output = self.run_contract(FIXTURES / name)
                expected = (FIXTURES /
                            f"{name}.verify.out").read_text(encoding="utf-8")
                self.assertEqual(code, 0)
                self.assertEqual(output, expected)

    def test_remote_write_requires_confirmation_and_call_user_reason(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_codex_goal.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["next_action"] = "push"
        data["ll_contract"]["exit"]["privileged_git_exit"] = False
        data["ll_contract"]["exit"][
            "remote_write_requires_confirmation"] = False
        data["runtime_binding"]["call_user_when"] = ["scope_change"]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_REMOTE_CONFIRMATION", output)
        self.assertIn(
            "FAIL E_CALL_USER remote write requires call_user_when remote_write",
            output)

    def test_engineering_exit_privileged_git_exit_allows_remote_action(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_codex_goal.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["next_action"] = "push"
        data["ll_contract"]["exit"][
            "remote_write_requires_confirmation"] = False
        data["runtime_binding"]["call_user_when"] = ["scope_change"]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
            self.assertEqual(code, 0)
            self.assertIn("PASS ll.contract.v0", output)

    def test_uncompileable_reply_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "contract.ll"
            initialized = subprocess.run(
                [str(LEDGER), "init", str(FIXTURES / "base_ll_contract.json"),
                 str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            event_path = root / "event.json"
            event_path.write_text(
                json.dumps({
                    "type": "reply_compiled",
                    "result": {
                        "status": "maybe",
                        "summary": "差不多完成了",
                        "evidence": [],
                    },
                }),
                encoding="utf-8",
            )
            appended = subprocess.run(
                [str(LEDGER), "append", str(ledger), "--event-file",
                 str(event_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, appended.returncode)
            self.assertIn("reply_compiled result.status must be one of",
                          appended.stderr)

    def test_root_amendment_becomes_the_hot_root_after_explicit_rebind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "contract.ll"
            initialized = subprocess.run(
                [str(LEDGER), "init", str(FIXTURES / "base_ll_contract.json"),
                 str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)

            events = [
                {"type": "root_amendment", "goal": "用户修改后的主目标"},
                {"type": "hot_rejected", "reason": "root_goal_changed"},
                {
                    "type": "session_rebind",
                    "from_session_id": "old-thread",
                    "to_session_id": "new-thread",
                },
            ]
            for index, event in enumerate(events):
                event_path = root / f"root-event-{index}.json"
                event_path.write_text(json.dumps(event), encoding="utf-8")
                appended = subprocess.run(
                    [str(LEDGER), "append", str(ledger), "--event-file",
                     str(event_path)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, appended.returncode, appended.stderr)

            hot = render_hot_block(load_path(ledger), ledger)
            self.assertIn("Root: 用户修改后的主目标", hot)
            self.assertIn("Focus: 用户修改后的主目标", hot)

    def test_full_contract_requires_authorization_boundary(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        del data["ll_contract"]["authorization"]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_REQUIRED_FIELD ll_contract.authorization.ask_before is required",
            output)
        self.assertIn(
            "FAIL E_REQUIRED_FIELD ll_contract.authorization.allowed_side_effects is required",
            output)

    def test_linttest_template_source_fails(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["verification"]["linttest_gate"][
            "status"] = "detected"
        data["ll_contract"]["verification"]["linttest_gate"][
            "source"] = "template"
        data["ll_contract"]["verification"]["linttest_gate"]["executed"] = True
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_ENUM ll_contract.verification.linttest_gate.source has unsupported value 'template'",
            output)
        self.assertIn(
            "FAIL E_LINTTEST_GUESS linttest gate source cannot be a template or copied example",
            output)
        self.assertIn(
            "FAIL E_LINTTEST_AUTHORIZATION linttest execution requires user_request or contract_acceptance authorization",
            output)

    def test_done_requires_verification_evidence(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "done"
        data["ll_contract"]["exit"]["next_action"] = "report"
        data["ll_contract"]["verification"]["commands"] = []
        data["ll_contract"]["verification"]["substitute_evidence"] = []
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_DONE_VERIFICATION done requires verification commands or substitute evidence",
            output)

    def test_active_contract_requires_continue_action(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "active"
        data["ll_contract"]["exit"]["next_action"] = "report"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_ACTIVE_NEXT_ACTION", output)

    def test_codex_goal_requires_explicit_authorization(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_codex_goal.json").read_text(encoding="utf-8"))
        data["dispatch"].pop("goal_authorization")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_GOAL_AUTHORIZATION codex_goal requires dispatch.goal_authorization",
            output)

    def test_codex_goal_rejects_chat_text_as_objective_source(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_codex_goal.json").read_text(encoding="utf-8"))
        data["dispatch"]["goal_authorization"][
            "objective_source"] = "confirmation_text"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_GOAL_AUTHORIZATION codex_goal objective_source must be verified_contract",
            output)

    def test_current_task_feedback_cannot_claim_no_task_impact(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["feedback"] = [{
            "id": "ll-feedback-20260701-002",
            "source": "user",
            "quote": "把 acceptance 改成必须跑 smoke",
            "type": "current_task_correction",
            "problem": "acceptance changed",
            "disposition": "captured",
            "current_task_impact": "none",
        }]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_FEEDBACK_SCHEMA feedback[0].current_task_correction cannot have current_task_impact=none",
            output)

    def test_loop_control_feedback_must_be_absorbed_before_ready_exit(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["feedback"] = [{
            "id": "ll-feedback-20260701-004",
            "source": "user",
            "quote": "needs_human 后继续时没有恢复 loop",
            "type": "loop_process_gap",
            "applies_to": "loop-ledger",
            "target_artifact": "skills/loop-ledger/SKILL.md",
            "problem": "resume control rule is missing",
            "proposed_change": "keep the exact contract path bound before continuing",
            "disposition": "captured",
            "current_task_impact": "none",
        }]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_LOOP_FEEDBACK_UNRESOLVED", output)

    def test_scope_feedback_cannot_exit_done_while_captured(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "done"
        data["ll_contract"]["exit"]["next_action"] = "report"
        data["feedback"] = [{
            "id": "ll-feedback-20260701-005",
            "source": "user",
            "quote": "漏了历史筛选规则",
            "type": "loop_process_gap",
            "problem": "acceptance missed existing behavior",
            "disposition": "captured",
            "current_task_impact": "updates_acceptance",
        }]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_FEEDBACK_UNRESOLVED", output)

    def test_existing_capability_inventory_requires_acceptance_sources(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["target"]["existing_capability_inventory"] = {
            "prior_entries": ["scripts/old-ticket-report"],
            "behavior_rules": ["status prefix 【处理中】 counts as active"],
            "runtime_data_sources": [],
            "runtime_integrations": [],
            "domain_roles": [],
            "counterexamples": [],
        }
        data["ll_contract"]["verification"].pop("acceptance_sources", None)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_ACCEPTANCE_PROVENANCE", output)

    def test_acceptance_sources_preserve_done_when_one_to_one(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        done_when = data["ll_contract"]["verification"]["done_when"]
        done_when.append("all required artifacts have verification evidence")
        data["ll_contract"]["verification"]["acceptance_sources"] = [{
            "done_when": done_when[0],
            "source_type": "user_feedback",
            "evidence": "confirmed FF acceptance",
        }]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_ACCEPTANCE_PRESERVATION", output)

    def test_done_fails_with_unresolved_checkpoint(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "done"
        data["ll_contract"]["exit"]["next_action"] = "report"
        data["ll_contract"]["checkpoints"][0]["status"] = "pending"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn("FAIL E_CHECKPOINT_UNRESOLVED", output)

    def test_next_ff_ready_requires_next_ff_action(self):
        data = json.loads(
            (FIXTURES /
             "engineering_exit_manual_report.json").read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "next_ff_ready"
        data["ll_contract"]["exit"]["next_action"] = "report"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            code, output = self.run_contract(Path(tmp.name))
        self.assertEqual(code, 1)
        self.assertIn(
            "FAIL E_NEXT_FF next_ff_ready requires exit.next_action=next_ff",
            output)


if __name__ == "__main__":
    unittest.main()
