from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PaperIrSpecTest(unittest.TestCase):
    def test_architecture_documents_paper_ir_and_controlled_views(self) -> None:
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        views_readme = (ROOT / "template" / "_paperops" / "notes" / "views" / "README.md").read_text(
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
        combined = "\n".join(
            (
                ROOT / "template" / ".agents" / "skills" / name / "SKILL.md"
            ).read_text(encoding="utf-8")
            for name in [
                "finish-manuscript",
                "compile-results-section",
                "compile-discussion-section",
                "compile-methods-section",
            ]
        )

        for required in [
            "paper_ir",
            "compile-results-section",
            "compile-discussion-section",
            "compile-methods-section",
            "Writer に生の card ontology を直接渡さない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_section_contracts_define_io_not_prose_templates(self) -> None:
        contracts_root = ROOT / "template" / "_paperops" / "defaults" / "contracts"
        expected_files = [
            "README.md",
            "introduction.yml",
            "methods.yml",
            "results.yml",
            "discussion.yml",
            "conclusion.yml",
        ]
        for name in expected_files:
            with self.subTest(name=name):
                self.assertTrue((contracts_root / name).is_file())
        self.assertTrue((ROOT / "template" / "_paperops" / "contracts" / "README.md").is_file())

        methods = (contracts_root / "methods.yml").read_text(encoding="utf-8")
        for required in [
            "information_placement",
            "main_text",
            "supplement",
            "code_or_manifest",
            "verification_or_convergence",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, methods)

        results = (contracts_root / "results.yml").read_text(encoding="utf-8")
        for required in [
            "reader_question",
            "answer",
            "evidence",
            "scope",
            "consequence",
            "run_inventory_as_topic_sentence",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, results)

        discussion = (contracts_root / "discussion.yml").read_text(encoding="utf-8")
        for required in [
            "mechanism_hypothesis",
            "alternative_explanation",
            "implication",
            "prediction",
            "limitation",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, discussion)

    def test_writing_profile_overlays_section_contracts(self) -> None:
        profile = (ROOT / "template" / "manuscript" / "writing-profile.yml").read_text(
            encoding="utf-8"
        )
        gitignore = (ROOT / "template" / ".gitignore").read_text(encoding="utf-8")
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

        self.assertIn("paper_type: computational_modeling", profile)
        self.assertIn("geometry_and_boundary_conditions", profile)
        self.assertIn("state_variables_and_update_law", profile)
        self.assertIn("estimator_definition", profile)
        self.assertIn(".paperops/cache/", gitignore)
        self.assertIn("contracts/", architecture)
        self.assertIn("manuscript/writing-profile.yml", architecture)

    def test_skill_catalog_classifies_route_and_leaf_skills(self) -> None:
        catalog = (ROOT / "docs" / "skill-catalog.md").read_text(encoding="utf-8")

        self.assertIn("Route-level skills", catalog)
        self.assertIn("Leaf skills", catalog)
        self.assertIn("finish-manuscript", catalog)
        self.assertIn("paragraph-surgery", catalog)


if __name__ == "__main__":
    unittest.main()
