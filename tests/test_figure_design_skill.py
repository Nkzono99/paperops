from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FigureDesignSkillTemplateTest(unittest.TestCase):
    def test_design_paper_figure_skill_encodes_reader_task_and_design_principles(self) -> None:
        skill = read_template("template/.agents/skills/design-paper-figure/SKILL.md")

        for required in [
            "reader_task",
            "takeaway_sentence",
            "claim_or_decision",
            "encoding_choice",
            "scale_and_denominator",
            "uncertainty_or_distribution",
            "caption_plan",
            "annotation_plan",
            "color_accessibility",
            "runops_handoff",
            "acceptance_criteria",
            "データがあるから図にしない",
            "graphical perception",
            "distribution",
            "caption",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

    def test_figure_card_exposes_design_brief_for_individual_figures(self) -> None:
        figure_card = read_template("template/_paperops/evidence/figures/figure-card-template.md")

        for required in [
            "design_review",
            "reader_task",
            "takeaway_sentence",
            "encoding_choice",
            "scale_and_denominator",
            "uncertainty_or_distribution",
            "caption_plan",
            "color_accessibility",
            "runops_handoff",
            "acceptance_criteria",
            "## Figure design brief",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, figure_card)

    def test_existing_figure_flow_routes_to_design_skill(self) -> None:
        plan = read_template("template/.agents/skills/plan-figure-story/SKILL.md")
        audit = read_template("template/.agents/skills/figure-story-audit/SKILL.md")
        finish = read_template("template/.agents/skills/finish-manuscript/SKILL.md")
        roster = read_template("template/_paperops/defaults/workflow/subagent-roster.yml")

        for text in [plan, audit, finish, roster]:
            with self.subTest(text=text[:40]):
                self.assertIn("design-paper-figure", text)

    def test_claude_wrapper_and_downstream_docs_expose_design_skill(self) -> None:
        wrapper = read_template("template/.claude/skills/design-paper-figure/SKILL.md")
        docs = "\n".join(
            [
                read_template("docs/skill-catalog.md"),
                read_template("docs/architecture.md"),
                read_template("docs/current-specification.md"),
                read_template("template/AGENTS.md"),
                read_template("template/CLAUDE.md"),
                read_template("template/README.md"),
                read_template("CHANGELOG.md"),
            ]
        )

        self.assertIn("@${CLAUDE_SKILL_DIR}/../../../.agents/skills/design-paper-figure/SKILL.md", wrapper)
        for required in [
            "design-paper-figure",
            "図の設計意図",
            "reader task",
            "runops handoff",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs)


if __name__ == "__main__":
    unittest.main()
