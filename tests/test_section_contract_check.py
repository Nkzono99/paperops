from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-section-contracts.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class SectionContractCheckTest(unittest.TestCase):
    def test_non_strict_warns_when_results_hierarchy_lacks_reader_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer:
                - quantitative evidence and unit of analysis:
                - figure / table role:
                - baseline / comparator rationale:
                - consequence:

                ## Discussion functions

                - principal_finding: Baseline charging can alter the work budget.
                - mechanism_warrant: The retained charge changes the force balance.
                - prior_work_delta: This separates the local control from prior ambient-field estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control is a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and compare the same criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | draft |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | draft |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | draft |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | draft |
                """,
            )

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("one-sentence answer", result.stdout)
        self.assertIn("baseline / comparator rationale", result.stdout)

    def test_strict_fails_when_any_legacy_results_item_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer:
                - quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
                - figure / table role: Figure 2 shows the work budget.
                - baseline / comparator rationale: The control isolates retained charge.
                - consequence: The next item tests coupling.
                - reader question 2: Does the criterion survive coupling?
                - one-sentence answer: It survives only inside the stated boundary.
                - quantitative evidence and unit of analysis: 8 of 16 trajectories, per candidate.
                - figure / table role: Figure 3 shows the boundary.
                - baseline / comparator rationale: The coupled case tests the omitted process.
                - consequence: The Discussion interprets the boundary.

                ## Discussion functions

                - principal_finding: Baseline charging changes the work budget.
                - mechanism_warrant: Retained charge changes the force balance.
                - prior_work_delta: This separates local control from ambient estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control defines a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and reuse the criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | locked |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | locked |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | locked |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | locked |
                """,
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Results hierarchy item `1`", result.stdout)
        self.assertIn("one-sentence answer", result.stdout)

    def test_strict_fails_when_legacy_results_hierarchy_has_no_recognizable_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                The baseline result is described here as narrative prose only.

                ## Discussion functions

                - principal_finding: Baseline charging changes the work budget.
                - mechanism_warrant: Retained charge changes the force balance.
                - prior_work_delta: This separates local control from ambient estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control defines a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and reuse the criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | locked |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | locked |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | locked |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | locked |
                """,
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Results hierarchy item `1`", result.stdout)
        self.assertIn("reader question", result.stdout)

    def test_strict_fails_when_discussion_functions_are_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer: It changes the work budget under the stated control.
                - quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
                - figure / table role: Figure 2 shows the work budget.
                - baseline / comparator rationale: The no-forcing control isolates retained charge.
                - consequence: The next section tests whether the same criterion survives coupling.

                ## Discussion functions

                - principal_finding:
                - mechanism_warrant: TBD
                - prior_work_delta:
                - alternative_or_boundary:
                - implication:
                - decisive_next_test:

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | draft |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | draft |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | draft |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | draft |
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("discussion", result.stdout)
        self.assertIn("mechanism_warrant", result.stdout)
        self.assertIn("decisive_next_test", result.stdout)

    def test_strict_fails_when_methods_definition_registry_is_missing_required_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer: It changes the work budget under the stated control.
                - quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
                - figure / table role: Figure 2 shows the work budget.
                - baseline / comparator rationale: The no-forcing control isolates retained charge.
                - consequence: The next section tests whether the same criterion survives coupling.

                ## Discussion functions

                - principal_finding: Baseline charging can alter the work budget.
                - mechanism_warrant: The retained charge changes the force balance.
                - prior_work_delta: This separates the local control from prior ambient-field estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control is a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and compare the same criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | draft |
                | decision_criteria |  | methods.criteria.01 | draft |
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Methods definition registry", result.stdout)
        self.assertIn("comparison_or_baseline", result.stdout)
        self.assertIn("decision_criteria", result.stdout)

    def test_strict_passes_when_storyline_section_contracts_are_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer: It changes the work budget under the stated control.
                - quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
                - figure / table role: Figure 2 shows the work budget.
                - baseline / comparator rationale: The no-forcing control isolates retained charge while not testing coupled illumination.
                - consequence: The next section tests whether the same criterion survives coupling.

                ## Discussion functions

                - principal_finding: Baseline charging can alter the work budget.
                - mechanism_warrant: The retained charge changes the force balance.
                - prior_work_delta: This separates the local control from prior ambient-field estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control is a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and compare the same criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | locked |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | locked |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | locked |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | locked |
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("section contracts", result.stdout)


if __name__ == "__main__":
    unittest.main()
