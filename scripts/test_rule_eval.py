#!/usr/bin/env python3
"""Main-path regression for the rule-eval CLI against a fake Rollerskate CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rule_eval  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "rule-eval"
# Fake rs: validate/start/inspect/cancel. inspect answers from the workspace RULE.md, so each arm gets its own choices.
FAKE_RS = r'''#!/usr/bin/env python3
import json, sys, pathlib
log = pathlib.Path(__file__).with_name("calls.log")
log.open("a").write(" ".join(sys.argv[1:3]) + "\n")
command = sys.argv[2]
if command == "validate":
    print(json.dumps({"status": "valid"}))
elif command == "start":
    intent = json.load(open(sys.argv[3]))
    arm = "candidate" if "candidate" in intent["requestId"] else "baseline"
    pathlib.Path(__file__).with_name(arm + ".intent").write_text(json.dumps(intent))
    print(json.dumps({"status": "accepted", "run": {"runId": "run-" + arm}}))
elif command == "inspect":
    arm = sys.argv[3].removeprefix("run-")
    intent = json.loads(pathlib.Path(__file__).with_name(arm + ".intent").read_text())
    rule = pathlib.Path(intent["workspaceRef"].removeprefix("file://"), "RULE.md").read_text()
    nodes = []
    for node in intent["graph"]["nodes"][:-1]:
        scenario = node["id"].split("_")[0]
        choice = "B" if "new" in rule else ("A" if scenario == "s1" else "B")
        if node["executor"] == "other" and arm == "candidate":
            nodes.append({"node": {"id": node["id"]}, "status": "failed", "value": None})
            continue
        nodes.append({"node": {"id": node["id"]}, "status": "succeeded",
                      "value": {"summary": json.dumps({node["id"] + "-choice": {"scenario": scenario, "choice": choice}} if arm == "candidate" else {"scenario": scenario, "choice": choice})}})
    print(json.dumps({"summary": {"runId": sys.argv[3], "status": "needs_human"}, "graphNodes": nodes}))
elif command == "cancel":
    print(json.dumps({"status": "cancelled"}))
'''


class RuleEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.rs = self.base / "fake-rs"
        self.rs.write_text(FAKE_RS)
        self.rs.chmod(0o755)
        spec_dir = self.base / "spec"
        (spec_dir / "rules").mkdir(parents=True)
        (spec_dir / "rules" / "baseline.md").write_text("old rule")
        (spec_dir / "rules" / "candidate.md").write_text("new rule")
        for scenario in ("s1", "s2"):
            (spec_dir / "scenarios" / scenario).mkdir(parents=True)
            (spec_dir / "scenarios" / scenario / "CONTEXT.md").write_text("context " + scenario)
        self.spec = spec_dir / "spec.json"
        self.spec.write_text(json.dumps({
            "schema": "rule-eval.spec.v1", "id": "demo",
            "arms": {"baseline": "rules/baseline.md", "candidate": {"rule": "rules/candidate.md", "effort": "high"}},
            "agents": [{"id": "codex", "ref": "agent:codex", "effort": "low", "target": True},
                       {"id": "other", "ref": "agent:pi-ds"}],
            "samples": 2,
            "scenarios": [{"id": "s1", "choices": ["A", "B"], "expected": "B", "holdout": False},
                          {"id": "s2", "choices": ["A", "B"], "expected": "B", "holdout": True}]}))

    def run_cli(self, *args: str) -> dict:
        env = dict(os.environ, AI_META_USAGE_DIR=str(self.base / "usage"))
        result = subprocess.run([str(SCRIPT), *args, "--rs", str(self.rs)], capture_output=True, text=True,
                                env=env, check=True)
        return json.loads(result.stdout)

    def test_start_then_collect_scores_arms_blindly(self) -> None:
        record = self.run_cli("start", str(self.spec))
        run_dir = Path(record["run_dir"])
        candidate = json.loads((self.base / "candidate.intent").read_text())
        workspace = Path(candidate["workspaceRef"].removeprefix("file://"))
        # Each arm sees only its own rule and never the expected answers.
        self.assertEqual("new rule", (workspace / "RULE.md").read_text())
        self.assertNotIn("expected", "".join(p.read_text() for p in workspace.rglob("*.md")))
        self.assertEqual(9, len(candidate["graph"]["nodes"]))
        self.assertEqual({"effort": "high"}, candidate["graph"]["nodes"][0]["selection"])

        result = self.run_cli("collect", str(run_dir))
        self.assertEqual("pass", result["verdict"])
        self.assertEqual({"codex": "2/4", "other": "2/4"}, result["scores"]["baseline"])
        self.assertEqual({"codex": "4/4", "other": "0/4"}, result["scores"]["candidate"])
        self.assertTrue(result["runs"]["candidate"]["cancelled"])
        self.assertTrue((run_dir / "result.json").is_file())
        self.assertEqual(2, (self.base / "calls.log").read_text().count("run cancel"))

    def test_ambiguous_or_invalid_wrapped_choices_remain_invalid(self) -> None:
        self.assertIsNone(rule_eval.parse_choice({"one": {"choice": "A"}, "two": {"choice": "B"}}, ["A", "B"]))
        self.assertIsNone(rule_eval.parse_choice({"one": {"choice": "Z"}}, ["A", "B"]))
        self.assertIsNone(rule_eval.parse_choice({"one": "B"}, ["A", "B"]))

    def test_target_gain_with_other_agent_regression_is_split(self) -> None:
        spec = {"agents": [{"id": "codex", "target": True}, {"id": "claude"}], "samples": 1,
                "scenarios": [{"id": "s1"}]}

        def cell(choice: str) -> dict:
            return {"status": "succeeded", "choice": choice, "correct": choice == "B"}
        table = {"baseline": {"s1_codex_1": cell("A"), "s1_claude_1": cell("B")},
                 "candidate": {"s1_codex_1": cell("B"), "s1_claude_1": cell("A")}}
        self.assertEqual("split", rule_eval.verdict(spec, table)[0])
        table["candidate"]["s1_codex_1"] = cell("A")
        self.assertEqual("fail", rule_eval.verdict(spec, table)[0])


if __name__ == "__main__":
    unittest.main()
