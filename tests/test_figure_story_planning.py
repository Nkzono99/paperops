from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class FigureStoryPlanningTemplateTest(unittest.TestCase):
    def test_template_has_figure_contract_and_story_planning_skill(self) -> None:
        contract = read_template("template/_paperops/defaults/contracts/figures.yml")
        skill = read_template("template/.agents/skills/plan-figure-story/SKILL.md")
        profile = read_template("template/manuscript/writing-profile.yml")
        machine = read_template("template/_paperops/defaults/workflow/machine.yml")
        current_state = read_template("template/_paperops/workflow/current-state.yml")
        makefile = read_template("template/Makefile")

        for required in [
            "visual_obligations",
            "model_or_state_visualization",
            "estimator_or_decision_criterion",
            "primary_evidence",
            "mechanism_or_boundary_comparison",
            "sensitivity_default: supplement",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, "\n".join([contract, skill, profile]))

        for required in [
            "figure_candidate_inventory_complete",
            "visual_obligations_satisfied",
            "main_figure_roles_covered",
            "figure_story_human_approved",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, machine)
                self.assertIn(required, current_state)

        self.assertIn("figure-obligation-check", makefile)
        self.assertIn("scripts/check-figure-obligations.py --root .", makefile)

    def test_claim_and_figure_templates_expose_visual_obligation_crosswalk(self) -> None:
        claim = read_template("template/_paperops/claims/claims/claim-card-template.md")
        figure = read_template("template/_paperops/evidence/figures/figure-card-template.md")

        for required in [
            "visual_obligations",
            "no_figure_reason",
            "satisfies_visual_obligations",
            "current_manuscript_role",
            "missing_action",
            "main / supplement / notes-only / removed",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, claim + "\n" + figure)

    def test_finish_manuscript_routes_through_plan_figure_story_before_drafting(self) -> None:
        finish = read_template("template/.agents/skills/finish-manuscript/SKILL.md")
        catalog = read_template("docs/skill-catalog.md")
        architecture = read_template("docs/architecture.md")

        for required in [
            "plan-figure-story",
            "figure-obligation-check",
            "visual obligation",
            "本文生成前",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, "\n".join([finish, catalog, architecture]))


if __name__ == "__main__":
    unittest.main()
