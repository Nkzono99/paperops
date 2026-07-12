from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class IssueGuardTemplateTest(unittest.TestCase):
    def test_scientific_gate_covers_assumptions_stress_and_external_gates(self) -> None:
        card = read_template("template/_paperops/defaults/schemas/research-gate.schema.json")
        skill = read_template("template/.agents/skills/scientific-gate/SKILL.md")
        combined = card + "\n" + skill

        for required in [
            "central_assumptions",
            "claim_stress_tests",
            "external_validation_gates",
            "path_criterion",
            "evidence_design",
            "allowed wording",
            "must-not-claim",
            "validated scope",
            "not covered",
            "claim support ではなく claim upgrade blocker",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_figure_card_and_audit_cover_denominator_path_and_state_visualization(self) -> None:
        card = read_template("template/_paperops/defaults/schemas/research-figure.schema.json")
        skill = read_template("template/.agents/skills/figure-story-audit/SKILL.md")
        combined = card + "\n" + skill

        for required in [
            "endpoint != reachability",
            "cumulative criterion",
            "threshold barrier",
            "same denominator",
            "independence caveat",
            "max-comparison",
            "verification coverage",
            "state variable visualized",
            "outcome-only figure risk",
            "state visualization is not comparator",
            "diagnostic-only",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_starter_scientific_gates_avoid_project_specific_path_examples(self) -> None:
        combined = "\n".join(
            [
                read_template("template/_paperops/defaults/contracts/figures.yml"),
                read_template("template/_paperops/defaults/schemas/research-gate.schema.json"),
                read_template("template/_paperops/notes/views/scientific-gate.md"),
                read_template("template/_paperops/defaults/schemas/research-figure.schema.json"),
                read_template("template/.agents/skills/figure-story-audit/SKILL.md"),
            ]
        )

        for forbidden in [
            "release / detachment",
            "detachment",
            "lofting",
            "W_final",
            "from-rest",
            "force threshold",
            "charge distribution",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

    def test_peer_review_response_and_notes_require_closure_and_prose_explanations(self) -> None:
        response_card = read_template("template/_paperops/defaults/schemas/issue-response.schema.json")
        peer_view = read_template("template/_paperops/notes/views/peer-review.md")
        peer_skill = read_template("template/.agents/skills/peer-review-manuscript/SKILL.md")
        respond_skill = read_template("template/.agents/skills/respond-to-peer-review/SKILL.md")
        collect_skill = read_template("template/.agents/skills/collect-manuscript-review/SKILL.md")
        note_skill = read_template("template/.agents/skills/note-writing-session/SKILL.md")
        combined = "\n".join(
            [response_card, peer_view, peer_skill, respond_skill, collect_skill, note_skill]
        )

        for required in [
            "closure_status",
            "not_closed_reason",
            "next_required_evidence",
            "resolution_route",
            "prose explanation",
            "scientific-blocker",
            "readability-blocker",
            "figure-rendering-blocker",
            "public-vocabulary-blocker",
            "line-level public readability",
            "source-of-truth language",
            "rendered figure",
            "anti-defensive prose",
            "raw comment を保存せず",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
