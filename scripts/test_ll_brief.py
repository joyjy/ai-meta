from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("ll-brief")
LEDGER = Path(__file__).with_name("ll-ledger")
FIXTURE = (Path(__file__).with_name("fixtures") / "ll-contracts" /
           "engineering_exit_codex_goal.json")


class LLBriefTest(unittest.TestCase):

    def active_contract(self) -> dict:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["ll_contract"]["exit"]["state"] = "active"
        data["ll_contract"]["exit"]["next_action"] = "continue"
        data["ll_contract"]["exit"]["remote_write_requires_confirmation"] = True
        data["ll_contract"]["exit"].pop("privileged_git_exit", None)
        data["dispatch"]["target"] = "manual"
        data["runtime_binding"]["hot_packet"] = {
            "protocol": "ll-turn@1",
            "soft_target": 1200,
            "hard_limit": 1800,
        }
        data["ll_contract"]["checkpoints"][0]["status"] = "passed"
        data["ll_contract"]["checkpoints"][1]["status"] = "pending"
        return data

    def run_brief(self, data: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "contract.json"
            ledger = root / "contract.ll"
            source.write_text(json.dumps(data), encoding="utf-8")
            initialized = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            return subprocess.run(
                [str(SCRIPT), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_renders_exactly_eight_hot_path_lines(self):
        result = self.run_brief(self.active_contract())
        self.assertEqual(0, result.returncode, result.stderr)
        lines = result.stdout.rstrip("\n").splitlines()
        self.assertEqual(8, len(lines))
        self.assertTrue(lines[0].startswith("LL: "))
        self.assertTrue(lines[1].startswith("Root: "))
        self.assertTrue(lines[2].startswith("Focus: "))
        self.assertTrue(lines[3].startswith("Local done: "))
        self.assertTrue(lines[4].startswith("Scope: "))
        self.assertTrue(lines[5].startswith("Guardrails: "))
        self.assertTrue(lines[6].startswith("Reply: "))
        self.assertEqual(
            "Contract: active goal binds exact path; never infer newest.",
            lines[-1],
        )
        self.assertNotIn("…", result.stdout)
        self.assertIn("one active focus", lines[5])
        self.assertIn("ask before=scope change", lines[5])
        self.assertNotIn("knowledge_gate", result.stdout)
        self.assertNotIn("risk_chain_markers", result.stdout)
        self.assertIn("ll-turn@1", lines[6])
        self.assertNotIn("status=continue|completed|blocked|needs_human",
                         lines[6])
        self.assertNotIn(str(Path.home()), result.stdout)
        self.assertLessEqual(len(result.stdout.rstrip("\n")), 1200)

    def test_rejects_overlong_hot_block_without_truncating_semantics(self):
        data = self.active_contract()
        data["ll_contract"]["verification"]["done_when"] = ["x" * 1800]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "contract.json"
            ledger = root / "contract.ll"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("hot-packet preflight failed", result.stderr)
        self.assertIn("hard_limit=1800", result.stderr)
        self.assertIn("without dropping required semantics", result.stderr)
        self.assertNotIn("…", result.stderr)

    def test_legacy_hot_packet_policy_keeps_its_embedded_budget(self):
        data = self.active_contract()
        data["runtime_binding"]["hot_packet"] = {
            "protocol": "ll-turn@1",
            "soft_target": 800,
            "hard_limit": 1200,
        }
        self.assertEqual(0, self.run_brief(data).returncode)
        data["ll_contract"]["verification"]["done_when"] = ["x" * 1200]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "contract.json"
            ledger = root / "contract.ll"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [str(LEDGER), "init", str(source), str(ledger)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("hard_limit=1200", result.stderr)

    def test_rejects_invalid_contract(self):
        data = self.active_contract()
        del data["ll_contract"]["authorization"]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                         suffix=".json") as tmp:
            json.dump(data, tmp)
            tmp.flush()
            result = subprocess.run(
                [str(SCRIPT), tmp.name],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("contract verification failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
