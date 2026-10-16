from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ll_contract_file import load_path

SCRIPT = Path(__file__).with_name("ll-compile")


class LLCompileTest(unittest.TestCase):

    def test_compiles_ff_without_losing_acceptance_or_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ff.json"
            ledger = root / "session.ll"
            source.write_text(json.dumps({
                "project_root": str(root),
                "authorization_source": "user_request",
                "ff": {
                    "goal": "实现确定性编译",
                    "scope": {
                        "include": ["compiler", "tests", "compiler"],
                        "exclude": ["push"],
                    },
                    "acceptance": ["A 保真", "B 有来源", "A 保真"],
                    "verification_loop": {
                        "stop_conditions": ["C 回归通过"],
                    },
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [str(SCRIPT), str(ledger), "--input", str(source)],
                check=False, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            compiled = json.loads(result.stdout)
            self.assertTrue(compiled["preflight"]["ok"])
            contract = load_path(ledger).contract
            self.assertEqual(
                ["compiler", "tests"],
                contract["ll_contract"]["target"]["required_artifacts"],
            )
            verification = contract["ll_contract"]["verification"]
            self.assertEqual(["A 保真", "B 有来源", "C 回归通过"],
                             verification["done_when"])
            self.assertEqual(
                verification["done_when"],
                [item["done_when"]
                 for item in verification["acceptance_sources"]])
            self.assertEqual("user_request", contract["dispatch"][
                "goal_authorization"]["source"])
            self.assertIn("revision_sha256", contract["ff_binding"])
            self.assertTrue(contract["ff_binding"]["id"].startswith("ff-"))

    def test_continuation_semantics_become_done_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ff.json"
            ledger = root / "session.ll"
            source.write_text(json.dumps({
                "ff": {
                    "goal": "交付到既有会话",
                    "scope": {"include": ["idle desktop session"]},
                    "acceptance": ["消息完成交付"],
                    "continuation": {
                        "supported_targets": [{
                            "surface": "codex_desktop",
                            "activity": "idle",
                            "transport": "chat_session",
                        }],
                        "admission": "active target is rejected",
                        "queue_visibility": "none",
                        "completion_visibility": "target task transcript",
                        "idempotency": "delivery id is unique",
                    },
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                    "dispatch_target": "codex",
                },
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [str(SCRIPT), str(ledger), "--input", str(source)],
                check=False, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            done = load_path(ledger).contract["ll_contract"]["verification"][
                "done_when"]
            self.assertTrue(any("codex_desktop/idle" in item for item in done))
            self.assertTrue(any("idempotency" in item for item in done))

    def test_rejects_unready_or_blocked_ff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ff.json"
            source.write_text(json.dumps({
                "id": "blocked",
                "ff": {
                    "goal": "不要执行",
                    "acceptance": ["有结果"],
                    "blocking_questions": ["范围是什么"],
                    "ready_for_dispatch": False,
                },
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [str(SCRIPT), str(root / "session.ll"), "--input", str(source)],
                check=False, capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("ready_for_dispatch must be true", result.stderr)

    def test_preflight_reports_total_and_contributions_over_hard_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ff.json"
            source.write_text(json.dumps({
                "ff": {
                    "goal": "验证超限诊断",
                    "scope": {"include": ["范围" + "乙" * 1800]},
                    "acceptance": ["诊断完整"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [str(SCRIPT), str(root / "session.ll"), "--input", str(source),
                 "--preflight"],
                check=False, capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            for field in ["LL=", "Goal=", "Scope=", "Done=", "Guardrails=",
                          "Ordinary=", "Recovery=", "Contract="]:
                self.assertIn(field, result.stderr)
            self.assertIn("soft_target=1200", result.stderr)
            self.assertIn("hard_limit=1800", result.stderr)


if __name__ == "__main__":
    unittest.main()
