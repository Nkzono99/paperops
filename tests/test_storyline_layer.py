from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class StorylineLayerTemplateTest(unittest.TestCase):
    def test_template_has_storyline_contract_skill_view_and_workflow_guards(self) -> None:
        expected_paths = [
            "template/_paperops/defaults/contracts/storyline.yml",
            "template/_paperops/defaults/schemas/results-hierarchy.schema.json",
            "template/_paperops/model/editorial/results-hierarchy.yml",
            "template/_paperops/notes/views/storyline.md",
            "template/.agents/skills/design-paper-storyline/SKILL.md",
            "template/.claude/skills/design-paper-storyline/SKILL.md",
        ]
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists(), f"{path} is missing")

        combined = "\n".join(
            read_template(path)
            for path in [
                "template/_paperops/defaults/contracts/storyline.yml",
                "template/_paperops/notes/views/storyline.md",
                "template/.agents/skills/design-paper-storyline/SKILL.md",
                "template/_paperops/defaults/workflow/machine.yml",
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

    def test_template_has_typed_results_schema_and_starter_chain_field(self) -> None:
        schema_path = "template/_paperops/defaults/schemas/results-hierarchy.schema.json"
        model_path = "template/_paperops/model/editorial/results-hierarchy.yml"

        self.assertTrue((ROOT / schema_path).exists(), f"{schema_path} is missing")
        self.assertTrue((ROOT / model_path).exists(), f"{model_path} is missing")

        schema = json.loads(read_template(schema_path))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertEqual(schema["properties"]["items"]["minItems"], 1)
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["items"]["items"]["additionalProperties"])
        self.assertIn("next_item_id", schema["properties"]["items"]["items"]["required"])
        self.assertIn("next_item_id", read_template(model_path))

    def test_downstream_storyline_surfaces_explain_typed_results_migration(self) -> None:
        combined = "\n".join(
            read_template(path)
            for path in [
                "template/_paperops/notes/views/storyline.md",
                "template/_paperops/defaults/contracts/storyline.yml",
                "template/.agents/skills/design-paper-storyline/SKILL.md",
                "template/.agents/skills/compile-results-section/SKILL.md",
                "template/AGENTS.md",
                "template/CLAUDE.md",
                "template/README.md",
            ]
        )

        self.assertIn("_paperops/model/editorial/results-hierarchy.yml", combined)
        self.assertIn("typed Results hierarchy", combined)
        self.assertNotIn("legacy Markdown", read_template("template/_paperops/notes/views/storyline.md"))

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
