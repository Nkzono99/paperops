from __future__ import annotations

import unittest

from tests.helpers import ROOT


class P2DocumentationTest(unittest.TestCase):
    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_cli_docs_cover_public_commands_state_and_storage(self) -> None:
        text = self.text("docs/cli.md")
        for command in ("pops model status", "pops model validate", "pops model diff", "pops model adopt", "pops model rollback"):
            self.assertIn(command, text)
        for term in ("legacy-authoritative", "shadow-compare", "v2-authoritative", ".paperops/migrations/", ".paperops/snapshots/", "--dry-run", "--cascade", "recovery.conflict"):
            self.assertIn(term, text)

    def test_architecture_and_current_spec_mark_p2_complete_but_defer_p3_p4(self) -> None:
        architecture = self.text("docs/architecture.md")
        current = self.text("docs/current-specification.md")
        for text in (architecture, current):
            self.assertIn("P2", text)
            self.assertIn("typed", text)
            self.assertIn("workflow", text)
            self.assertIn("deterministic", text)
        self.assertIn("model migration", current)

    def test_migration_and_downstream_interfaces_explain_no_ai_boundary(self) -> None:
        migration = self.text("docs/migrations/v0.md")
        self.assertIn("M0-0005", migration)
        self.assertIn("guide-only", migration)
        for relative in ("template/README.md", "template/AGENTS.md", "template/CLAUDE.md"):
            text = self.text(relative)
            self.assertIn("pops model diff", text)
            self.assertIn("pops model adopt", text)
            self.assertIn("pops model rollback", text)
            self.assertIn("AI", text)
            self.assertIn("pops change", text)
            self.assertIn("workflow", text)

    def test_skill_and_disposition_docs_keep_legacy_writers(self) -> None:
        skill = self.text("docs/skill-catalog.md")
        disposition = self.text("docs/paperops2-disposition.md")
        self.assertIn("pops model", skill)
        self.assertIn("scientific", skill)
        self.assertIn("P2", disposition)
        self.assertIn("legacy", disposition)
        self.assertIn("P3", disposition)
        self.assertIn("P4", disposition)

    def test_shadow_and_snapshot_state_are_ignored(self) -> None:
        for relative in (".gitignore", "template/.gitignore"):
            text = self.text(relative)
            self.assertIn(".paperops/migrations/", text)
            self.assertIn(".paperops/snapshots/", text)


if __name__ == "__main__":
    unittest.main()
