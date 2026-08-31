from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
WORKITEM = ROOT / "ll-workitem"
HOT = ROOT / "ll-hot-block"


class LLWorkItemTest(unittest.TestCase):

    def test_init_compiles_dispatch_ready_workitem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "workitem.ll"
            payload = root / "workitem.json"
            payload.write_text(json.dumps({
                "id": "lintest",
                "title": "修复 session 生命周期",
                "project_root": str(root),
                "gitlab_flow": "l3",
                "ff": {
                    "goal": "稳定复用 Codex session",
                    "scope": {
                        "include": ["runner", "ledger"],
                        "exclude": ["dashboard redesign"],
                    },
                    "acceptance": ["重复 Run 不创建 session"],
                    "checks": ["mix test"],
                    "blocking_questions": [],
                    "ready_for_dispatch": True,
                },
            }), encoding="utf-8")
            initialized = subprocess.run(
                [str(WORKITEM), "init", str(ledger), "--input", str(payload)],
                check=False, capture_output=True, text=True)
            self.assertEqual(0, initialized.returncode, initialized.stderr)

            hot = subprocess.run(
                [str(HOT), str(ledger)], check=False,
                capture_output=True, text=True)
            self.assertEqual(0, hot.returncode, hot.stderr)
            self.assertIn("Root: 稳定复用 Codex session", hot.stdout)
            self.assertIn("Focus: 稳定复用 Codex session", hot.stdout)


if __name__ == "__main__":
    unittest.main()
