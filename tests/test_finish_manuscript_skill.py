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
            "content-first",
            "storyline",
            "design-paper-storyline",
            "editorial architect",
            "Submission hygiene",
            "下流 manuscript goal 中に readiness-check",
            "feedback-paper-harness",
            "feedback loop",
            "scientific-gate",
            "design-manuscript-claims",
            "integrate-writing-feedback",
            "peer-review-manuscript",
            "respond-to-peer-review",
            "review-public-manuscript",
            "human approval",
            "Finish criteria",
            "Start self-critique",
            "Course-correction checkpoint",
            "Completion self-critique",
            "check-content-first.py",
            "finish-manuscript-check",
            "next_action_reduces_content_blocker",
            "Orchestrator/subagent mode",
            "workflow/subagent-roster.yml",
            "main agent",
            "orchestrator",
            "story_architect",
            "evidence_auditor",
            "results_structure_reviewer",
            "discussion_function_reviewer",
            "public_reader",
            "submission_hygienist",
            "subagent reports are not manuscript edits",
            "integration decision",
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
