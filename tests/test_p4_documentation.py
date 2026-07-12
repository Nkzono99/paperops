from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class P4DocumentationTest(unittest.TestCase):
    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_public_docs_cover_projection_issue_approval_and_cutover(self) -> None:
        combined = self.text("docs/architecture.md") + self.text("docs/cli.md") + self.text("docs/migrations/v0.md")
        for phrase in ("INGESTED", "PUBLISHABLE", "workflow issue route", "workflow approval decide", "workflow migrate diff", "v2-authoritative", "owner-local"):
            self.assertIn(phrase, combined)

    def test_generated_workflow_state_is_ignored_in_root_and_scaffold(self) -> None:
        self.assertIn(".paperops/workflow/", self.text(".gitignore"))
        self.assertIn(".paperops/workflow/", self.text("template/.gitignore"))

    def test_downstream_guidance_uses_typed_cli_for_routine_routing(self) -> None:
        combined = self.text("template/README.md") + self.text("template/AGENTS.md") + self.text("template/.agents/skills/route-manuscript-feedback/SKILL.md")
        self.assertIn("pops workflow issue route", combined)
        self.assertIn("pops workflow apply", combined)
        self.assertIn("legacy", combined)

    def test_changelog_has_migration_note(self) -> None:
        changelog = self.text("CHANGELOG.md")
        self.assertIn("P4", changelog)
        self.assertIn(".paperops/workflow/", changelog)


if __name__ == "__main__":
    unittest.main()
