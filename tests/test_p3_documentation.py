from __future__ import annotations

import unittest

from tests.helpers import ROOT


class P3DocumentationTest(unittest.TestCase):
    def text(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_public_docs_define_compile_write_and_typed_cutover(self) -> None:
        for relative in (
            "README.md", "docs/architecture.md", "docs/cli.md",
            "docs/current-specification.md", "docs/skill-catalog.md",
            "template/README.md", "template/AGENTS.md", "template/CLAUDE.md",
        ):
            with self.subTest(relative=relative):
                text = self.text(relative)
                self.assertIn("typed", text.lower())
                self.assertIn("pops compile", text)
                self.assertIn("pops write", text)
        cli = self.text("docs/cli.md")
        for action in ("start", "status", "check", "diff", "apply", "rollback"):
            self.assertIn(f"pops write {action}", cli)

    def test_writer_skills_keep_direct_tex_and_global_replan_boundary(self) -> None:
        for name in (
            "compile-results-section", "compile-discussion-section",
            "compile-methods-section", "design-paper-storyline", "review-block-flow",
        ):
            text = self.text(f"template/.agents/skills/{name}/SKILL.md")
            self.assertIn("pops write", text)
            self.assertIn("candidate", text)
            self.assertTrue("再compile" in text or "recompile" in text)
        migration = self.text("docs/migrations/v0.md")
        for term in ("opt-in", "living TeX", "P4", "P7", ".paperops/writer/"):
            self.assertIn(term, migration)

    def test_generated_state_is_ignored_in_root_and_downstream(self) -> None:
        for relative in (".gitignore", "template/.gitignore"):
            text = self.text(relative)
            for path in (".paperops/compile/", ".paperops/compile-diagnostics/", ".paperops/writer/"):
                self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
