from __future__ import annotations

import tempfile
import unittest

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-card-coverage.py"


class CardCoverageCheckTest(unittest.TestCase):
    def test_template_card_coverage_check_is_advisory_by_default(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("card-coverage-check", result.stdout)

    def test_strict_mode_reports_unregistered_figures_citations_and_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            result_path = root / "manuscript" / "en" / "sections" / "30_results.tex"
            result_path.write_text(
                "\\section{Results}\n"
                "% block: results.new_claim.01\n"
                "Figure~\\ref{fig:new} cites \\cite{Key2026}.\n"
                "\\begin{figure}[ht]\n"
                "\\includegraphics{../shared/figures/new.png}\n"
                "\\caption{New figure.}\n"
                "\\label{fig:new}\n"
                "\\end{figure}\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("unregistered figure asset", result.stdout)
        self.assertIn("new.png", result.stdout)
        self.assertIn("unregistered citation key", result.stdout)
        self.assertIn("Key2026", result.stdout)
        self.assertIn("unregistered manuscript block", result.stdout)
        self.assertIn("results.new_claim.01", result.stdout)

    def test_registered_cards_satisfy_strict_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            result_path = root / "manuscript" / "en" / "sections" / "30_results.tex"
            result_path.write_text(
                "\\section{Results}\n"
                "% block: results.new_claim.01\n"
                "Figure~\\ref{fig:new} cites \\cite{Key2026}.\n"
                "\\begin{figure}[ht]\n"
                "\\includegraphics{../shared/figures/new.png}\n"
                "\\caption{New figure.}\n"
                "\\label{fig:new}\n"
                "\\end{figure}\n",
                encoding="utf-8",
            )
            figure_card = root / "_paperops" / "evidence" / "figures" / "FIG-9001.md"
            figure_card.write_text(
                "---\n"
                "id: FIG-9001\n"
                "type: figure\n"
                "figure_ref: \"manuscript/shared/figures/new.png\"\n"
                "manuscript_blocks:\n"
                "  - results.new_claim.01\n"
                "---\n",
                encoding="utf-8",
            )
            result_card = root / "_paperops" / "evidence" / "results" / "RES-9001.md"
            result_card.write_text(
                "---\n"
                "id: RES-9001\n"
                "type: result\n"
                "manuscript_blocks:\n"
                "  - results.new_claim.01\n"
                "---\n",
                encoding="utf-8",
            )
            source_card = root / "_paperops" / "evidence" / "sources" / "SRC-9001.md"
            source_card.write_text(
                "---\n"
                "id: SRC-9001\n"
                "type: source\n"
                "citation_keys:\n"
                "  - Key2026\n"
                "---\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("coverage gaps are not detected", result.stdout)


if __name__ == "__main__":
    unittest.main()
