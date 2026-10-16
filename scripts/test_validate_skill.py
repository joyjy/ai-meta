from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("validate-skill")


def load_module():
    loader = importlib.machinery.SourceFileLoader("validate_skill", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class ValidateSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_repo_skill_detection_excludes_external_skill(self):
        self.assertTrue(
            self.mod.is_ai_meta_skill(
                self.mod.REPO_ROOT / "skills" / "save-context"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(self.mod.is_ai_meta_skill(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
