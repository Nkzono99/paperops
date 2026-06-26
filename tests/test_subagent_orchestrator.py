from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SubagentOrchestratorTemplateTest(unittest.TestCase):
    def test_template_defines_subagent_roster_contract(self) -> None:
        roster_path = ROOT / "template" / "_paperops" / "workflow" / "subagent-roster.yml"
        self.assertTrue(roster_path.exists(), "subagent roster contract is missing")

        roster = json.loads(roster_path.read_text(encoding="utf-8"))
        self.assertEqual(roster["schema_version"], 1)
        self.assertEqual(roster["mode"], "orchestrated_manuscript_writing")
        self.assertIn("orchestrator", roster)
        self.assertIn("delegation_contract", roster)
        self.assertIn("integration_contract", roster)

        role_ids = {role["id"] for role in roster["roles"]}
        for required in [
            "story_architect",
            "evidence_auditor",
            "results_structure_reviewer",
            "discussion_function_reviewer",
            "figure_story_reviewer",
            "public_reader",
            "reviewer_panel",
            "submission_hygienist",
        ]:
            with self.subTest(role=required):
                self.assertIn(required, role_ids)

        submission_role = next(
            role for role in roster["roles"] if role["id"] == "submission_hygienist"
        )
        self.assertIn("STRUCTURE_ACCEPTED", submission_role["entry_condition"])
        self.assertIn("no story/section/evidence blocker remains", submission_role["entry_condition"])

        public_reader = next(role for role in roster["roles"] if role["id"] == "public_reader")
        self.assertNotIn("manuscript/ja/", public_reader["allowed_inputs"])
        self.assertNotIn("manuscript/en/", public_reader["allowed_inputs"])
        self.assertTrue(
            all("public" in item or "sanitized" in item for item in public_reader["allowed_inputs"]),
            public_reader["allowed_inputs"],
        )
        self.assertIn(
            "direct concurrent edits to the same manuscript block",
            roster["orchestrator"]["must_not_delegate"],
        )

        for role in roster["roles"]:
            with self.subTest(role=role["id"]):
                self.assertIn("allowed_inputs", role)
                self.assertIn("outputs", role)
                self.assertIn("route_bias", role)

    def test_review_templates_capture_subagent_delegation_and_integration(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "template/_paperops/review/rounds/review-round-template.md",
                "template/_paperops/review/feedback/feedback-card-template.md",
                "template/_paperops/notes/views/peer-review.md",
            ]
        )

        for required in [
            "Subagent delegation ledger",
            "delegated_role",
            "integration decision",
            "orchestrator",
            "subagent_report",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_downstream_docs_expose_orchestrator_mode(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "template/AGENTS.md",
                "template/CLAUDE.md",
                "template/README.md",
                "docs/skill-catalog.md",
                "docs/architecture.md",
            ]
        )

        for required in [
            "_paperops/workflow/subagent-roster.yml",
            "orchestrator",
            "subagent",
            "integration decision",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
