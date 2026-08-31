from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import yaml


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

    def test_sanitize_removes_only_ai_meta_frontmatter_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source" / "sample-skill"
            destination = root / "copy" / "sample-skill"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\n"
                "name: sample-skill\n"
                "description: Sample description\n"
                "disable-model-invocation: true\n"
                "metadata:\n  owner: test\n"
                "---\n\n# Sample\n",
                encoding="utf-8",
            )

            self.mod.sanitize_skill_copy(source, destination)

            content = (destination / "SKILL.md").read_text(encoding="utf-8")
            frontmatter = yaml.safe_load(content.split("---", 2)[1])
            self.assertEqual("sample-skill", frontmatter["name"])
            self.assertEqual({"owner": "test"}, frontmatter["metadata"])
            self.assertNotIn("disable-model-invocation", frontmatter)
            self.assertIn("# Sample", content)

    def test_repo_skill_detection_excludes_external_skill(self):
        self.assertTrue(
            self.mod.is_ai_meta_skill(
                self.mod.REPO_ROOT / "skills" / "save-context"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(self.mod.is_ai_meta_skill(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
