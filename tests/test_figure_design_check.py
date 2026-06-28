from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, make_var_tokens, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-figure-design.py"


def write_figure_card(root: Path, body: str) -> Path:
    figures = root / "_paperops" / "evidence" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    path = figures / "FIG-9001.md"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


class FigureDesignCheckTest(unittest.TestCase):
    def test_strict_flags_main_claim_figure_with_unchecked_design_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_figure_card(
                root,
                """\
                ---
                id: FIG-9001
                type: figure
                status: draft
                figure_ref: "fig:main"
                supports_claims: [CLM-9001]
                uses_results: [RES-9001]
                manuscript_blocks: [results.main]
                current_manuscript_role: main
                satisfies_visual_obligations: [VO-9001]
                design_review:
                  reader_task: unchecked
                  takeaway_sentence: unchecked
                  claim_or_decision: unchecked
                  encoding_choice: unchecked
                  scale_and_denominator: unchecked
                  uncertainty_or_distribution: unchecked
                  annotation_caption: unchecked
                  color_accessibility: unchecked
                  runops_handoff: unchecked
                  acceptance_criteria: unchecked
                ---

                # FIG-9001
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reader_task", result.stdout)
        self.assertIn("acceptance_criteria", result.stdout)

    def test_passes_completed_main_figure_design_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_figure_card(
                root,
                """\
                ---
                id: FIG-9001
                type: figure
                status: ready
                figure_ref: "fig:main"
                supports_claims: [CLM-9001]
                uses_results: [RES-9001]
                manuscript_blocks: [results.main]
                current_manuscript_role: main
                satisfies_visual_obligations: [VO-9001]
                design_review:
                  reader_task: compare the primary endpoint across conditions
                  takeaway_sentence: condition A shifts the endpoint relative to baseline
                  claim_or_decision: supports CLM-9001 within the stated denominator
                  encoding_choice: shared-axis line plot with direct labels
                  scale_and_denominator: normalized by the same simulated condition set
                  uncertainty_or_distribution: show run-to-run spread as a band
                  annotation_caption: caption names the denominator and threshold
                  color_accessibility: colorblind-safe palette with redundant labels
                  runops_handoff: generated from export bundle IMP-9001
                  acceptance_criteria: reader can identify baseline, threshold, and uncertainty
                ---

                # FIG-9001
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("figure design review に問題は見つかりませんでした", result.stdout)

    def test_skips_notes_only_or_removed_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_figure_card(
                root,
                """\
                ---
                id: FIG-9001
                type: figure
                status: draft
                figure_ref: ""
                supports_claims: [CLM-9001]
                current_manuscript_role: notes-only
                design_review:
                  reader_task: unchecked
                  acceptance_criteria: unchecked
                ---

                # FIG-9001
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_makefiles_wire_figure_design_check_to_audit_and_finish(self) -> None:
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for makefile in [root_makefile, template_makefile]:
            with self.subTest(makefile=makefile[:20]):
                self.assertIn("figure-design-check:", makefile)
                self.assertIn("check-figure-design.py", makefile)
                self.assertIn("check-figure-design.py --root", makefile)
                self.assertIn("--strict", makefile)

        self.assertIn("figure-design-check", make_var_tokens(root_makefile, "SMOKE_CHECKS"))
        self.assertIn("figure-design-check", make_var_tokens(root_makefile, "FINISH_MANUSCRIPT_CHECKS"))
        self.assertIn("figure-design-check", make_var_tokens(template_makefile, "AUDIT_CHECKS"))
        self.assertIn("figure-design-check", make_var_tokens(template_makefile, "FINISH_MANUSCRIPT_CHECKS"))


if __name__ == "__main__":
    unittest.main()
