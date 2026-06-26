from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinishManuscriptSkillTest(unittest.TestCase):
    SPECIALIST_SKILLS = [
        "content-first-gate",
        "orchestrate-manuscript-subagents",
        "route-manuscript-feedback",
        "compile-results-section",
        "compile-discussion-section",
        "compile-methods-section",
        "finalize-manuscript",
    ]

    def test_finish_manuscript_skill_is_thin_orchestrator(self) -> None:
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
            "design-paper-storyline",
            "editorial architect",
            "plan-figure-story",
            "paper_ir",
            "compile-results-section",
            "compile-discussion-section",
            "compile-methods-section",
            "Submission hygiene",
            "feedback loop",
            "scientific-gate",
            "design-manuscript-claims",
            "integrate-writing-feedback",
            "peer-review-manuscript",
            "respond-to-peer-review",
            "review-public-manuscript",
            "human approval",
            "content-first-gate",
            "orchestrate-manuscript-subagents",
            "route-manuscript-feedback",
            "finalize-manuscript",
            "Finish criteria",
            "main agent",
            "orchestrator",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

        for inlined_detail in [
            "## Orchestrator/subagent mode",
            "### compile-results",
            "### compile-discussion",
            "### compile-methods",
            "## Backward propagation",
            "## Codex 実行メモ",
        ]:
            with self.subTest(inlined_detail=inlined_detail):
                self.assertNotIn(inlined_detail, skill)
        self.assertLessEqual(
            len(skill.splitlines()),
            95,
            "finish-manuscript should stay a compact router; move detail to specialist skills",
        )

        wrapper = wrapper_path.read_text(encoding="utf-8")
        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/finish-manuscript/SKILL.md",
            wrapper,
        )

        catalog = catalog_path.read_text(encoding="utf-8")
        self.assertIn("finish-manuscript", catalog)

    def test_split_specialist_skills_exist_and_keep_detailed_contracts(self) -> None:
        expected_terms = {
            "content-first-gate": [
                "Start self-critique",
                "Course-correction checkpoint",
                "Completion self-critique",
                "check-content-first.py",
                "finish-manuscript-check",
                "next_action_reduces_content_blocker",
                "feedback-paper-harness",
            ],
            "orchestrate-manuscript-subagents": [
                "_paperops/defaults/workflow/subagent-roster.yml",
                "story_architect",
                "evidence_auditor",
                "results_structure_reviewer",
                "discussion_function_reviewer",
                "public_reader",
                "submission_hygienist",
                "subagent reports are not manuscript edits",
                "integration decision",
            ],
            "route-manuscript-feedback": [
                "Issue Router",
                "route-review",
                "Backward propagation",
                "evidence_loop",
                "story_loop",
                "section_loop",
                "submission_hygiene_only",
            ],
            "compile-results-section": [
                "paper_ir",
                "reader question -> one-sentence answer -> quantitative evidence -> figure -> consequence",
                "section-depth-check",
                "Results hierarchy",
                "one-paragraph subsections",
            ],
            "compile-discussion-section": [
                "paper_ir",
                "observation",
                "mechanism_hypothesis",
                "prior_work_delta",
                "decisive_next_test",
                "Discussion functions",
            ],
            "compile-methods-section": [
                "paper_ir",
                "method unit",
                "main_text",
                "supplement",
                "code_or_manifest",
                "writing-profile.yml",
            ],
            "finalize-manuscript": [
                "Finish criteria",
                "mirror-check",
                "citation-check",
                "ai-disclosure-check",
                "pre-submit",
                "STRUCTURE_ACCEPTED",
            ],
        }

        for skill_name in self.SPECIALIST_SKILLS:
            with self.subTest(skill=skill_name):
                skill_path = ROOT / "template" / ".agents" / "skills" / skill_name / "SKILL.md"
                wrapper_path = ROOT / "template" / ".claude" / "skills" / skill_name / "SKILL.md"
                self.assertTrue(skill_path.exists(), f"{skill_name} skill is missing")
                self.assertTrue(wrapper_path.exists(), f"Claude wrapper for {skill_name} is missing")

                skill = skill_path.read_text(encoding="utf-8")
                self.assertIn(f"name: {skill_name}", skill)
                for required in expected_terms[skill_name]:
                    self.assertIn(required, skill)

                wrapper = wrapper_path.read_text(encoding="utf-8")
                self.assertIn(
                    f"@${{CLAUDE_SKILL_DIR}}/../../../.agents/skills/{skill_name}/SKILL.md",
                    wrapper,
                )


if __name__ == "__main__":
    unittest.main()
