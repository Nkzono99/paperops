from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-public-terms.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class PublicTermsCheckTest(unittest.TestCase):
    def test_default_guard_rejects_internal_analysis_labels_in_public_manuscript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "en" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe target-snapshot sample and saved batch define the exposure diagnostic.\n"
                + "This table is not used for ranking and is not evidence.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("target-snapshot sample", result.stdout)
        self.assertIn("exposure diagnostic", result.stdout)
        self.assertIn("not evidence", result.stdout)
        self.assertIn("replacement", result.stdout)

    def test_non_strict_warns_when_first_definition_location_lacks_definition_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "manuscript" / "mirror" / "terminology.yml",
                """
                terms:
                  - id: BEACH
                    ja: "BEACH"
                    en_public: "BEACH"
                    status: "needs_definition"
                    first_definition_required: true
                    first_definition_location: "manuscript/en/sections/20_methods.tex"
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "20_methods.tex",
                """
                The BEACH result is used as the charging calculation input.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("definition sentence", result.stdout)
        self.assertIn("BEACH", result.stdout)

    def test_strict_fails_when_first_definition_location_lacks_definition_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "manuscript" / "mirror" / "terminology.yml",
                """
                terms:
                  - id: BEACH
                    ja: "BEACH"
                    en_public: "BEACH"
                    status: "needs_definition"
                    first_definition_required: true
                    first_definition_location: "manuscript/en/sections/20_methods.tex"
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "20_methods.tex",
                """
                The BEACH result is used as the charging calculation input.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("definition sentence", result.stdout)

    def test_strict_passes_when_first_definition_location_contains_definition_sentence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "manuscript" / "mirror" / "terminology.yml",
                """
                terms:
                  - id: BEACH
                    ja: "BEACH"
                    en_public: "BEACH"
                    status: "needs_definition"
                    first_definition_required: true
                    first_definition_location: "manuscript/en/sections/20_methods.tex"
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "20_methods.tex",
                """
                BEACH refers to the three-dimensional surface-charging calculation used to estimate facet charges.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
