from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class StorylineLayerTemplateTest(unittest.TestCase):
    def test_template_has_storyline_contract_skill_view_and_workflow_guards(self) -> None:
        expected_paths = [
            "template/contracts/storyline.yml",
            "template/notes/views/storyline.md",
            "template/.agents/skills/design-paper-storyline/SKILL.md",
            "template/.claude/skills/design-paper-storyline/SKILL.md",
        ]
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists(), f"{path} is missing")

        combined = "\n".join(
            read_template(path)
            for path in [
                "template/contracts/storyline.yml",
                "template/notes/views/storyline.md",
                "template/.agents/skills/design-paper-storyline/SKILL.md",
                "template/workflow/machine.yml",
                "template/workflow/current-state.yml",
                "template/Makefile",
                "Makefile",
                "docs/skill-catalog.md",
                "docs/architecture.md",
            ]
        )
        for required in [
            "story_spine",
            "reader_promise",
            "evidence_ladder",
            "results_hierarchy",
            "discussion_functions",
            "mechanism_warrant",
            "prior_work_delta",
            "decisive_next_test",
            "storyline_architecture_approved",
            "storyline-check",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_writing_and_review_skills_route_through_editorial_architect_view(self) -> None:
        combined = "\n".join(
            read_template(path)
            for path in [
                "template/.agents/skills/finish-manuscript/SKILL.md",
                "template/.agents/skills/audit-ai-draft/SKILL.md",
                "template/.agents/skills/peer-review-manuscript/SKILL.md",
                "template/.agents/skills/review-public-manuscript/SKILL.md",
            ]
        )

        for required in [
            "design-paper-storyline",
            "editorial architect",
            "storyline",
            "Results hierarchy",
            "Discussion functions",
            "section-depth",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
