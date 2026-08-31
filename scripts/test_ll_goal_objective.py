from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("ll-goal-objective")
LEDGER = Path(__file__).with_name("ll-ledger")
FIXTURE = (Path(__file__).with_name("fixtures") / "ll-contracts" /
           "engineering_exit_codex_goal.json")


class LLGoalObjectiveTest(unittest.TestCase):

    def run_renderer(
            self, data: dict) -> tuple[subprocess.CompletedProcess[str], Path]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            contract_path = Path(tmp.name).resolve()
            result = subprocess.run(
                [str(SCRIPT), tmp.name],
                check=False,
                capture_output=True,
                text=True,
            )
            return result, contract_path

    def active_goal_contract(self) -> dict:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "active"
        data["ll_contract"]["exit"]["next_action"] = "continue"
        data["ll_contract"]["exit"][
            "remote_write_requires_confirmation"] = True
        data["ll_contract"]["exit"].pop("privileged_git_exit", None)
        data["dispatch"]["target"] = "manual"
        return data

    def test_renders_objective_and_exact_contract_path(self):
        data = self.active_goal_contract()
        result, contract_path = self.run_renderer(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(data["runtime_binding"]["objective"], result.stdout)
        self.assertIn(str(contract_path), result.stdout)
        self.assertIn("普通轮次只读取 LL 动态 hot block", result.stdout)
        self.assertIn("ll-brief", result.stdout)
        self.assertIn("append-only ledger", result.stdout)
        self.assertIn("done_when", result.stdout)

    def test_rejects_confirmation_reply_as_objective(self):
        data = self.active_goal_contract()
        data["runtime_binding"]["objective"] = "OK"
        result, _ = self.run_renderer(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot be a confirmation reply", result.stderr)

    def test_segmented_goal_reads_only_fixed_front_on_ordinary_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            ledger = root / "session.ll"
            source.write_text(json.dumps(self.active_goal_contract()),
                              encoding="utf-8")
            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            result = subprocess.run(
                [str(SCRIPT), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(
                f"{Path(__file__).with_name('ll-hot-block').resolve()} "
                f"{ledger.resolve()}", result.stdout)
            self.assertNotIn("head -n 8", result.stdout)
            self.assertIn("append-only ledger", result.stdout)

    def test_rejects_needs_human_contract(self):
        data = self.active_goal_contract()
        data["ll_contract"]["exit"]["state"] = "needs_human"
        data["ll_contract"]["exit"]["next_action"] = "manual"
        result, _ = self.run_renderer(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires exit.state=active", result.stderr)

    def test_rejects_manual_adapter(self):
        data = self.active_goal_contract()
        data["runtime_binding"]["adapter"] = "manual_report"
        data["dispatch"].pop("goal_authorization", None)
        result, _ = self.run_renderer(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn("adapter must be codex_goal", result.stderr)


if __name__ == "__main__":
    unittest.main()
