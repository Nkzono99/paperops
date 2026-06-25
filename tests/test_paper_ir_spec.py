from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PaperIrSpecTest(unittest.TestCase):
    def test_architecture_documents_paper_ir_and_controlled_views(self) -> None:
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        views_readme = (ROOT / "template" / "notes" / "views" / "README.md").read_text(
            encoding="utf-8"
        )

        for required in [
            "paper_ir",
            "section compiler",
            "controlled authoring view",
            "生成一時物",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, architecture)

        self.assertIn("pure overview view", views_readme)
        self.assertIn("controlled authoring view", views_readme)
        self.assertIn("concept-terms.md", views_readme)
        self.assertIn("condition-context-map.md", views_readme)

    def test_template_makefile_splits_ci_audit_and_pre_submit_profiles(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("audit:", makefile)
        self.assertNotIn("command -v", makefile)
        self.assertIn("PYTHON_BOOTSTRAP ?= python", makefile)
        self.assertIn("pre-submit: ci audit", makefile)
        self.assertRegex(makefile, r"(?m)^ci: .*build-ja build-en$", "ci should stay structural")
        self.assertRegex(
            makefile,
            r"(?m)^audit: .*concept-term-check.*argument-focus-check.*figure-reference-check",
            "audit should collect authoring checks",
        )
        self.assertIn("check-concept-terms.py --root . --strict", makefile)
        self.assertIn("check-figure-references.py --root . --strict", makefile)
        self.assertIn("check-external-imports.py --root . --strict", makefile)

    def test_finish_manuscript_routes_writer_through_paper_ir(self) -> None:
        skill = (
            ROOT / "template" / ".agents" / "skills" / "finish-manuscript" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for required in [
            "paper_ir",
            "compile-results",
            "compile-discussion",
            "compile-methods",
            "Writer に生の card ontology を直接渡さない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

    def test_skill_catalog_classifies_route_and_leaf_skills(self) -> None:
        catalog = (ROOT / "docs" / "skill-catalog.md").read_text(encoding="utf-8")

        self.assertIn("Route-level skills", catalog)
        self.assertIn("Leaf skills", catalog)
        self.assertIn("finish-manuscript", catalog)
        self.assertIn("paragraph-surgery", catalog)


if __name__ == "__main__":
    unittest.main()
