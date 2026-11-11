from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent
WORKITEM = ROOT / "ll-workitem"
TURN = ROOT / "ll-turn"
HOT = ROOT / "ll-hot-block"
LEDGER = ROOT / "ll-ledger"
LEGACY_FIXTURE = (
    ROOT / "fixtures" / "ll-contracts" / "engineering_exit_codex_goal.json")


def setUpModule():
    usage = tempfile.TemporaryDirectory()
    unittest.addModuleCleanup(usage.cleanup)
    patcher = mock.patch.dict(os.environ, {"AI_META_USAGE_DIR": usage.name})
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


class LLTurnTest(unittest.TestCase):

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args), check=False, capture_output=True, text=True)

    def write_json(self, path: Path, value: dict) -> Path:
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def init_ledger(self, root: Path, acceptance: list[str]) -> Path:
        ledger = root / "turn.ll"
        workitem = self.write_json(root / "workitem.json", {
            "id": "turn",
            "ff": {
                "goal": "完成验收跟踪",
                "acceptance": acceptance,
                "blocking_questions": [],
                "ready_for_dispatch": True,
            },
        })
        initialized = self.run_cli(
            str(WORKITEM), "init", str(ledger), "--input", str(workitem))
        self.assertEqual(0, initialized.returncode, initialized.stderr)
        return ledger

    def reply(self, root: Path, ledger: Path, status: str, **extra):
        payload = self.write_json(root / "reply.json", {
            "status": status,
            "summary": "本轮结果",
            "evidence": ["smoke passed"],
            "blocker": None,
            "next_focus": None,
            **extra,
        })
        return self.run_cli(
            str(TURN), "compile-reply", str(ledger), "--input", str(payload))

    def decide(self, root: Path, ledger: Path, decision: str):
        payload = self.write_json(root / "decision.json", {"decision": decision})
        return self.run_cli(
            str(TURN), "human-decision", str(ledger), "--input", str(payload))

    def hot_lines(self, ledger: Path) -> list[str]:
        rendered = self.run_cli(str(HOT), str(ledger))
        self.assertEqual(0, rendered.returncode, rendered.stderr)
        return rendered.stdout.rstrip("\n").splitlines()

    def test_structured_reply_advances_one_focus_and_reconciles_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "generic.ll"
            workitem = self.write_json(root / "workitem.json", {
                "id": "generic-turn",
                "project_root": str(root),
                "ff": {
                    "goal": "交付可恢复的多轮工作",
                    "acceptance": ["两个 Focus 均有证据"],
                    "checks": ["integration smoke"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(workitem))
            self.assertEqual(0, initialized.returncode, initialized.stderr)

            first_reply = self.write_json(root / "first.json", {
                "status": "continue",
                "summary": "第一段实现完成",
                "evidence": ["smoke A passed"],
                "blocker": None,
                "next_focus": {
                    "id": "verify",
                    "goal": "验证第二段主路径",
                    "done_when": ["smoke B passed"],
                },
            })
            advanced = self.run_cli(
                str(TURN), "compile-reply", str(ledger), "--input",
                str(first_reply))
            self.assertEqual(0, advanced.returncode, advanced.stderr)
            advanced_output = json.loads(advanced.stdout)
            self.assertIn("Focus: 验证第二段主路径", advanced_output["hot"])
            self.assertIn("Root: 交付可恢复的多轮工作", advanced_output["hot"])

            final_reply = self.write_json(root / "final.json", {
                "status": "completed",
                "summary": "第二段验证完成并回看 Root",
                "evidence": ["smoke B passed", "Root acceptance reconciled"],
                "blocker": None,
                "next_focus": None,
            })
            completed = self.run_cli(
                str(TURN), "compile-reply", str(ledger), "--input",
                str(final_reply))
            self.assertEqual(0, completed.returncode, completed.stderr)
            completed_output = json.loads(completed.stdout)
            self.assertTrue(any(
                "status=active" in line for line in completed_output["hot"]))
            self.assertIn(
                "Focus: 交付可恢复的多轮工作", completed_output["hot"])

            root_reply = self.write_json(root / "root.json", {
                "status": "completed",
                "summary": "Root 验收条件已逐项核对",
                "evidence": ["smoke A passed", "smoke B passed"],
                "acceptance_met": [{"index": 1, "evidence": "smoke A+B passed"}],
                "blocker": None,
                "next_focus": None,
            })
            reconciled = self.run_cli(
                str(TURN), "compile-reply", str(ledger), "--input",
                str(root_reply))
            self.assertEqual(0, reconciled.returncode, reconciled.stderr)
            reconciled_output = json.loads(reconciled.stdout)
            self.assertTrue(any(
                "status=completed" in line for line in reconciled_output["hot"]))
            self.assertIn("Focus: 无；等待人工处理", reconciled_output["hot"])

    def test_root_completion_requires_every_acceptance_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = self.init_ledger(root, ["接口跑通", "回读一致"])
            self.assertIn(
                "Local done: [1] 接口跑通、[2] 回读一致; "
                "then reconcile Root before terminal completion",
                self.hot_lines(ledger))

            first = self.reply(root, ledger, "continue", acceptance_met=[
                {"index": 1, "evidence": "smoke passed"}])
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertIn(
                "Local done: [2] 回读一致; "
                "then reconcile Root before terminal completion",
                json.loads(first.stdout)["hot"])

            before = ledger.read_text(encoding="utf-8")
            refused = self.reply(root, ledger, "completed")
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("[2] 回读一致", refused.stderr)
            root_focus = self.write_json(root / "root.json", {"focus_id": "root"})
            bypassed = self.run_cli(
                str(TURN), "complete-focus", str(ledger), "--input",
                str(root_focus))
            self.assertNotEqual(0, bypassed.returncode)
            superseded = self.run_cli(
                str(TURN), "supersede-focus", str(ledger), "--input",
                str(root_focus))
            self.assertNotEqual(0, superseded.returncode)
            exit_event = self.write_json(root / "exit.json", {
                "type": "exit", "state": "done", "next_action": "stop"})
            exited = self.run_cli(
                str(LEDGER), "append", str(ledger), "--event-file",
                str(exit_event))
            self.assertNotEqual(0, exited.returncode)
            self.assertIn("[2] 回读一致", exited.stderr)
            out_of_range = self.reply(root, ledger, "continue", acceptance_met=[
                {"index": 3, "evidence": "不存在的验收"}])
            self.assertNotEqual(0, out_of_range.returncode)
            self.assertEqual(before, ledger.read_text(encoding="utf-8"))

            completed = self.reply(root, ledger, "completed", acceptance_met=[
                {"index": 2, "evidence": "readback matched"}])
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue(any(
                "status=completed" in line
                for line in json.loads(completed.stdout)["hot"]))

    def test_user_decisions_stay_in_hot_block_as_whole_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = self.init_ledger(root, ["范围不扩大"])
            self.assertEqual("Decisions: none", self.hot_lines(ledger)[-1])

            for decision in ["保持交接范围", "暂缓真实 BPM 验证"]:
                recorded = self.decide(root, ledger, decision)
                self.assertEqual(0, recorded.returncode, recorded.stderr)
            lines = self.hot_lines(ledger)
            self.assertEqual(8, len(lines))
            self.assertEqual(
                "Decisions: 暂缓真实 BPM 验证；保持交接范围", lines[-1])

            for index in range(8):
                recorded = self.decide(root, ledger, f"决定{index}" + "细" * 200)
                self.assertEqual(0, recorded.returncode, recorded.stderr)
            lines = self.hot_lines(ledger)
            self.assertLessEqual(len("\n".join(lines)), 1800)
            self.assertIn("决定7", lines[-1])
            self.assertRegex(lines[-1], r"; \+\d+ more in ledger$")
            shown = lines[-1].split("; +")[0].removeprefix("Decisions: ")
            self.assertTrue(all(
                item.endswith("细" * 200) for item in shown.split("；")))

    def test_legacy_protocol_completes_without_acceptance_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
            exit_state = data["ll_contract"]["exit"]
            exit_state.update({
                "state": "active",
                "next_action": "continue",
                "remote_write_requires_confirmation": True,
            })
            exit_state.pop("privileged_git_exit", None)
            data["dispatch"]["target"] = "manual"
            data["runtime_binding"]["hot_packet"] = {
                "protocol": "ll-turn@1",
                "soft_target": 1200,
                "hard_limit": 1800,
            }
            source = self.write_json(root / "contract.json", data)
            ledger = root / "legacy.ll"
            initialized = self.run_cli(
                str(LEDGER), "init", str(source), str(ledger))
            self.assertEqual(0, initialized.returncode, initialized.stderr)

            completed = self.reply(root, ledger, "completed")
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue(any(
                "status=completed" in line
                for line in json.loads(completed.stdout)["hot"]))

    def test_hot_rejection_stops_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "generic.ll"
            payload = self.write_json(root / "workitem.json", {
                "id": "reject-hot",
                "ff": {
                    "goal": "保持 Root 不漂移",
                    "acceptance": ["Root 未被擅改"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(payload))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            rejection = self.write_json(
                root / "rejection.json", {"reason": "root_goal_changed"})
            rejected = self.run_cli(
                str(TURN), "reject-hot", str(ledger), "--input", str(rejection))
            self.assertEqual(0, rejected.returncode, rejected.stderr)
            output = json.loads(rejected.stdout)
            self.assertTrue(any(
                "status=hot_rejected" in line for line in output["hot"]))

    def test_overlong_next_focus_does_not_append_invalid_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "bounded.ll"
            payload = self.write_json(root / "workitem.json", {
                "id": "bounded-hot",
                "ff": {
                    "goal": "保持 packet 有界",
                    "acceptance": ["超限事件不写入 ledger"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(payload))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            before = ledger.read_text(encoding="utf-8")
            reply = self.write_json(root / "reply.json", {
                "status": "continue",
                "summary": "准备进入超长 Focus",
                "evidence": [],
                "blocker": None,
                "next_focus": {
                    "id": "too-long",
                    "goal": "x" * 1800,
                    "done_when": ["不得写入"],
                },
            })
            rejected = self.run_cli(
                str(TURN), "compile-reply", str(ledger), "--input", str(reply))
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("E_HOT_BLOCK", rejected.stderr)
            self.assertIn("hard_limit=1800", rejected.stderr)
            self.assertEqual(before, ledger.read_text(encoding="utf-8"))

    def test_goal_bound_root_rejects_in_place_amendment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "active.ll"
            workitem = self.write_json(root / "workitem.json", {
                "id": "active-amendment",
                "ff": {
                    "goal": "完成初始目标",
                    "acceptance": ["初始目标有证据"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(workitem))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            amendment = self.write_json(root / "amendment.json", {
                "actor": "user",
                "goal": "完成用户修订后的目标",
            })

            amended = self.run_cli(
                str(TURN), "amend-root", str(ledger), "--input",
                str(amendment))

            self.assertNotEqual(0, amended.returncode)
            self.assertIn("bound Codex goal cannot be amended in place",
                          amended.stderr)

    def test_goal_bound_structural_contract_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "active.ll"
            workitem = self.write_json(root / "workitem.json", {
                "id": "structural-patch",
                "ff": {
                    "goal": "完成初始目标",
                    "acceptance": ["初始目标有证据"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(workitem))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            event = self.write_json(root / "patch.json", {
                "type": "contract_patch",
                "patch": {
                    "ll_contract": {
                        "verification": {"done_when": ["新验收"]},
                    },
                },
            })
            rejected = self.run_cli(
                str(ROOT / "ll-ledger"), "append", str(ledger),
                "--event-file", str(event))
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("cannot rebind an active Codex goal", rejected.stderr)

    def test_completed_root_rejects_amendment_and_requires_new_ll(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "completed.ll"
            workitem = self.write_json(root / "workitem.json", {
                "id": "completed-amendment",
                "ff": {
                    "goal": "完成终态目标",
                    "acceptance": ["终态目标有证据"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            })
            initialized = self.run_cli(
                str(WORKITEM), "init", str(ledger), "--input", str(workitem))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            completed_reply = self.write_json(root / "completed.json", {
                "status": "completed",
                "summary": "Root 已完成",
                "evidence": ["终态目标有证据"],
                "acceptance_met": [{"index": 1, "evidence": "终态目标有证据"}],
                "blocker": None,
                "next_focus": None,
            })
            completed = self.run_cli(
                str(TURN), "compile-reply", str(ledger), "--input",
                str(completed_reply))
            self.assertEqual(0, completed.returncode, completed.stderr)
            amendment = self.write_json(root / "amendment.json", {
                "actor": "user",
                "goal": "增加新的结构性范围",
            })

            rejected = self.run_cli(
                str(TURN), "amend-root", str(ledger), "--input",
                str(amendment))

            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("completed LL cannot be amended or reopened",
                          rejected.stderr)
            self.assertIn("initialize a new LL", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
