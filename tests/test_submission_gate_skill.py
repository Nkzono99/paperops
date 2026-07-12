from __future__ import annotations

import unittest

from tests.helpers import ROOT


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class SubmissionGateSkillTemplateTest(unittest.TestCase):
    def test_submission_gate_skill_defines_two_axis_submission_model(self) -> None:
        skill = read_template("template/.agents/skills/submission-gate/SKILL.md")

        for required in [
            "submission-gate",
            "authoring source",
            "submission candidate",
            "living manuscript",
            "round snapshot",
            "revision-authoring",
            "revision-candidate",
            "submitted",
            "under-review",
            "PREDICTED-RESULT",
            "xx",
            "open AREQ",
            "check-predicted-results.py",
            "publication-model.yml",
            "submission/<venue>/round-",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

    def test_claude_wrapper_imports_submission_gate_skill(self) -> None:
        wrapper = read_template("template/.claude/skills/submission-gate/SKILL.md")

        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/submission-gate/SKILL.md",
            wrapper,
        )

    def test_docs_and_finish_routes_expose_submission_gate(self) -> None:
        docs = "\n".join(
            [
                read_template("docs/skill-catalog.md"),
                read_template("docs/architecture.md"),
                read_template("docs/current-specification.md"),
                read_template("template/AGENTS.md"),
                read_template("template/CLAUDE.md"),
                read_template("template/README.md"),
                read_template("template/.agents/skills/finish-manuscript/SKILL.md"),
                read_template("template/.agents/skills/finalize-manuscript/SKILL.md"),
                read_template("template/.agents/skills/draft-predicted-results/SKILL.md"),
                read_template("CHANGELOG.md"),
            ]
        )

        for required in [
            "submission-gate",
            "authoring source",
            "submission candidate",
            "revision-authoring",
            "round snapshot",
            "check-predicted-results.py",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs)

    def test_analysis_request_template_supports_prediction_lifecycle(self) -> None:
        template = read_template("template/_paperops/defaults/schemas/issue-analysis-request.schema.json")
        ledger = read_template("template/_paperops/defaults/schemas/publication-model.schema.json")

        for required in [
            '"planned"',
            "analysis_plan_frozen_commit",
            "data_not_seen_before_freeze",
            "planned_analysis",
            "prediction",
            "replacement",
            "execution_provenance",
            "reconciliation",
            "negative_null_route",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, template)

        for required in [
            "authoring",
            "submission_state",
            "revision_authoring",
            "revision_candidate",
            "source_commit",
            "gate_report_ref",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, ledger)


if __name__ == "__main__":
    unittest.main()
