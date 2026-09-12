from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "yargitay-research"


class SkillStructureTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        expected = [
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/yargitay.py",
            "references/yargitay-api.md",
            "references/research-method.md",
            "references/verification-and-citation.md",
        ]
        for relative_path in expected:
            with self.subTest(path=relative_path):
                self.assertTrue((SKILL / relative_path).is_file())

    def test_frontmatter_has_portable_name_and_description(self) -> None:
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name: yargitay-research$")
        self.assertRegex(frontmatter, r"(?m)^description: .+")
        self.assertIn("official Yargıtay", frontmatter)

    def test_references_are_routed_from_skill(self) -> None:
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for name in (
            "yargitay-api.md",
            "research-method.md",
            "verification-and-citation.md",
        ):
            with self.subTest(reference=name):
                self.assertIn(f"references/{name}", content)


if __name__ == "__main__":
    unittest.main()

