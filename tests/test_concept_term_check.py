from __future__ import annotations

import tempfile
import unittest

from tests.helpers import ROOT, copy_template, make_var_tokens, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-concept-terms.py"


def append_concept_row(project, row: str) -> None:
    view = project / "_paperops" / "notes" / "views" / "concept-terms.md"
    text = view.read_text(encoding="utf-8")
    marker = "| CT-0001 |"
    view.write_text(text.replace(marker, row + "\n" + marker), encoding="utf-8")


class ConceptTermCheckTest(unittest.TestCase):
    def test_strict_warns_on_unregistered_dense_concept_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "en" / "sections" / "20_method.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nImplementation acceleration, file formats, and random ledgers are left to the code/reproducibility package; "
                + "the manuscript defines only the surface-element charge update and the detachment-work estimator.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("未登録の概念語候補", result.stdout)
        self.assertIn("code/reproducibility package", result.stdout)
        self.assertIn("surface-element charge update", result.stdout)
        self.assertIn("detachment-work estimator", result.stdout)
        self.assertIn("一文に概念語候補", result.stdout)

    def test_registered_term_suppresses_unregistered_warning_but_flags_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            append_concept_row(
                target,
                "| CT-0100 | surface-element charge update | accepted | Methods | surface elements are updated by ... | surface element charge-update | `manuscript/en/sections/20_method.tex` | canonical wording fixed |",
            )
            section = target / "manuscript" / "en" / "sections" / "20_method.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe surface-element charge update is applied before detachment.\n"
                + "The same step is later called the surface element charge-update in the caption.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("表記揺れ候補", result.stdout)
        self.assertIn("surface-element charge update", result.stdout)
        self.assertIn("surface element charge-update", result.stdout)
        self.assertNotIn("未登録の概念語候補: `surface-element charge update`", result.stdout)

    def test_avoid_term_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            append_concept_row(
                target,
                "| CT-0200 | detachment-work estimator | avoid | Results | compute the work needed for detachment |  | `manuscript/en/sections/30_results.tex` | too compressed for public prose |",
            )
            section = target / "manuscript" / "en" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe detachment-work estimator is the main result.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("avoid", result.stdout)
        self.assertIn("detachment-work estimator", result.stdout)

    def test_missing_concept_term_view_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            (target / "_paperops" / "notes" / "views" / "concept-terms.md").unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/views/concept-terms.md", result.stdout)

    def test_makefiles_expose_concept_term_check(self) -> None:
        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        audit_checks = make_var_tokens(template_makefile, "AUDIT_CHECKS")
        smoke_checks = make_var_tokens(root_makefile, "SMOKE_CHECKS")

        self.assertIn("concept-term-check:", template_makefile)
        self.assertIn("check-concept-terms.py", template_makefile)
        self.assertIn("concept-term-check", audit_checks)
        self.assertIn("concept-term-check", smoke_checks)

    def test_concept_terms_are_connected_to_semantic_views_and_skills(self) -> None:
        combined = "\n".join(
            [
                (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8"),
                (ROOT / "docs" / "skill-catalog.md").read_text(encoding="utf-8"),
                (ROOT / "template" / "_paperops" / "notes" / "views" / "README.md").read_text(encoding="utf-8"),
                (ROOT / "template" / ".agents" / "skills" / "audit-ai-draft" / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "template" / ".agents" / "skills" / "polish-ai-draft" / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "template" / ".agents" / "skills" / "paragraph-surgery" / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "template" / ".agents" / "skills" / "public-terminology-pass" / "SKILL.md").read_text(encoding="utf-8"),
            ]
        )

        for required in [
            "_paperops/notes/views/concept-terms.md",
            "概念語ビュー",
            "claim / argument / evidence card",
            "concept-term-check",
            "concept-term compression",
            "普通の文へほどく",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
