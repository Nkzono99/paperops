from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-section-contracts.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


COMPLETE_DISCUSSION_AND_METHODS = """
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
"""

COMPLETE_LEGACY_RESULTS = """
## Results hierarchy

- reader question 1: What changes in the baseline?
- one-sentence answer: The work budget changes under the stated control.
- quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
- figure / table role: Figure 2 shows the work budget.
- baseline / comparator rationale: The control isolates retained charge.
- consequence: The next item tests coupling.
"""


def typed_result_item(item_id: str, next_item_id: str) -> dict[str, str]:
    return {
        "id": item_id,
        "reader_question": f"Reader question for {item_id}",
        "answer": f"Answer for {item_id}",
        "quantitative_evidence_and_unit_of_analysis": "12 of 16 trajectories, per candidate.",
        "figure_table_role": f"Figure for {item_id}",
        "baseline_comparator_rationale": "The control isolates the tested process.",
        "consequence": f"Consequence for {item_id}",
        "next_item_id": next_item_id,
    }


def write_typed_results(root: Path, items: list[object], *, schema_version: int = 1) -> None:
    write_text(
        root / "_paperops" / "model" / "editorial" / "results-hierarchy.yml",
        json.dumps({"schema_version": schema_version, "items": items}, ensure_ascii=False, indent=2),
    )


class SectionContractCheckTest(unittest.TestCase):
    def test_strict_passes_with_three_typed_results_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(
                root,
                [
                    typed_result_item("RHI-0001", "RHI-0002"),
                    typed_result_item("RHI-0002", "RHI-0003"),
                    typed_result_item("RHI-0003", ""),
                ],
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strict_fails_on_duplicate_typed_results_item_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(
                root,
                [
                    typed_result_item("RHI-0001", "RHI-0001"),
                    typed_result_item("RHI-0001", ""),
                ],
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate Results hierarchy item id `RHI-0001`", result.stdout)

    def test_strict_fails_on_broken_typed_results_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(
                root,
                [
                    typed_result_item("RHI-0001", "RHI-9999"),
                    typed_result_item("RHI-0002", ""),
                ],
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("next_item_id `RHI-9999`", result.stdout)

    def test_strict_fails_when_terminal_typed_results_item_has_next_item_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(root, [typed_result_item("RHI-0001", "RHI-0002")])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("terminal item `RHI-0001`", result.stdout)
        self.assertIn("next_item_id", result.stdout)

    def test_strict_fails_when_typed_results_schema_version_is_not_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(root, [typed_result_item("RHI-0001", "")], schema_version=2)
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("schema_version", result.stdout)
        self.assertIn("1", result.stdout)

    def test_strict_fails_when_typed_results_items_are_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(root, [])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("items", result.stdout)
        self.assertIn("non-empty list", result.stdout)

    def test_strict_fails_when_typed_results_item_is_not_a_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(root, ["not-a-mapping"])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("item `1`", result.stdout)
        self.assertIn("mapping", result.stdout)

    def test_strict_fails_when_typed_results_item_id_is_not_rhi_prefixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_typed_results(root, [typed_result_item("result-1", "")])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("item id `result-1`", result.stdout)
        self.assertIn("RHI-*", result.stdout)

    def test_strict_fails_when_typed_results_required_field_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            item = typed_result_item("RHI-0001", "")
            del item["consequence"]
            write_typed_results(root, [item])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("RHI-0001", result.stdout)
        self.assertIn("consequence", result.stdout)

    def test_non_strict_warns_on_typed_results_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
            )
            item = typed_result_item("RHI-0001", "")
            item["answer"] = "未記入"
            write_typed_results(root, [item])
            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("RHI-0001", result.stdout)
        self.assertIn("answer", result.stdout)

    def test_typed_results_hierarchy_does_not_fall_back_to_complete_legacy_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_LEGACY_RESULTS + COMPLETE_DISCUSSION_AND_METHODS,
            )
            item = typed_result_item("RHI-0001", "")
            item["answer"] = "未記入"
            write_typed_results(root, [item])
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("RHI-0001", result.stdout)
        self.assertIn("answer", result.stdout)

    def test_malformed_typed_results_hierarchy_does_not_fall_back_to_legacy_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "_paperops" / "notes" / "views" / "storyline.md",
                "# Storyline\n\n" + COMPLETE_LEGACY_RESULTS + COMPLETE_DISCUSSION_AND_METHODS,
            )
            write_text(
                root / "_paperops" / "model" / "editorial" / "results-hierarchy.yml",
                "schema_version: [1\nitems:\n  - id: RHI-0001\n",
            )
            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("`schema_version` は 1 である必要があります", result.stdout)
        self.assertIn("`items` must be a non-empty list", result.stdout)

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
