from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinishManuscriptSkillTest(unittest.TestCase):
    def test_finish_manuscript_skill_orchestrates_goal_manuscript_completion(self) -> None:
        skill_path = ROOT / "template" / ".agents" / "skills" / "finish-manuscript" / "SKILL.md"
        wrapper_path = ROOT / "template" / ".claude" / "skills" / "finish-manuscript" / "SKILL.md"
        catalog_path = ROOT / "docs" / "skill-catalog.md"

        self.assertTrue(skill_path.exists(), "finish-manuscript skill is missing")
        self.assertTrue(wrapper_path.exists(), "Claude wrapper for finish-manuscript is missing")

        skill = skill_path.read_text(encoding="utf-8")
        for required in [
            "name: finish-manuscript",
            "/goal",
            "1から",
            "既存稿",
            "feedback loop",
            "scientific-gate",
            "design-manuscript-claims",
            "integrate-writing-feedback",
            "peer-review-manuscript",
            "respond-to-peer-review",
            "review-public-manuscript",
            "human approval",
            "Finish criteria",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

        wrapper = wrapper_path.read_text(encoding="utf-8")
        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/finish-manuscript/SKILL.md",
            wrapper,
        )

        catalog = catalog_path.read_text(encoding="utf-8")
        self.assertIn("finish-manuscript", catalog)


if __name__ == "__main__":
    unittest.main()
