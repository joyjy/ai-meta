from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
COMPILER = ROOT / "ll-compile"
GOAL_RENDERER = ROOT / "ll-goal-objective"
CASES = ROOT / "fixtures" / "ll-goal-evals.json"


class LLGoalBehaviorEvalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES.read_text(encoding="utf-8"))

    def test_confirmed_ff_is_declared_completely_in_goal_and_hot_block(self):
        for case in self.cases:
            with self.subTest(case=case["name"]), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "ff.json"
                ledger = root / "session.ll"
                ff = json.loads(json.dumps(case["ff"]))
                ff["blocking_questions"] = []
                ff["ready_for_dispatch"] = True
                source.write_text(json.dumps({
                    "id": case["name"],
                    "authorization_source": "user_confirmation",
                    "ff": ff,
                }, ensure_ascii=False), encoding="utf-8")
                initialized = subprocess.run(
                    [str(COMPILER), str(ledger), "--input", str(source)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, initialized.returncode, initialized.stderr)

                front_lines = ledger.read_text(encoding="utf-8").splitlines()[:8]
                front = "\n".join(front_lines)
                self.assertEqual(8, len(front_lines))
                self.assertNotIn("…", front)
                self.assertIn(case["ff"]["goal"], front)
                for value in case["ff"]["scope"]["include"]:
                    self.assertIn(value, front)
                for value in case["ff"]["scope"]["exclude"]:
                    self.assertIn(value, front)
                for value in case["ff"]["acceptance"]:
                    self.assertIn(value, front)
                for value in case["expected_binding"]["allowed_side_effects"]:
                    self.assertIn(value.replace("_", " "), front_lines[4])
                for value in case["expected_binding"]["ask_before"]:
                    self.assertIn(value.replace("_", " "), front_lines[4])

                objective = subprocess.run(
                    [str(GOAL_RENDERER), str(ledger)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, objective.returncode, objective.stderr)
                self.assertIn(f"执行并完成：{case['ff']['goal']}",
                              objective.stdout)
                self.assertIn(
                    f"{(ROOT / 'll-hot-block').resolve()} {ledger.resolve()}",
                    objective.stdout)


if __name__ == "__main__":
    unittest.main()
