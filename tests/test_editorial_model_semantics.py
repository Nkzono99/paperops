from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paperops_editorial import (  # noqa: E402
    validate_editorial_references,
    validate_editorial_semantics,
    validate_extension_keys,
)


def story(story_id: str, status: str, move_ids: list[str]) -> dict[str, object]:
    return {
        "id": story_id,
        "label": f"Story {story_id}",
        "thesis": f"Thesis {story_id}",
        "result_order": ["RHI-0001"],
        "argument_move_ids": move_ids,
        "status": status,
        "selection_reason": "This is the clearest account." if status == "selected" else "",
        "rejection_reason": "The evidence is less direct." if status == "rejected" else "",
    }


def move(move_id: str, position: int, next_move_id: str) -> dict[str, object]:
    return {
        "id": move_id,
        "position": position,
        "stance": "assert",
        "reader_question": f"What does {move_id} establish?",
        "assertion": f"{move_id} establishes the main result.",
        "claim_ids": [],
        "result_item_ids": ["RHI-0001"],
        "next_move_id": next_move_id,
    }


def valid_documents() -> tuple[dict[str, object], dict[str, object]]:
    editorial: dict[str, object] = {
        "schema_version": 1,
        "model_id": "EDT-0001",
        "revision": 1,
        "reader_transformation": {
            "reader_before": "The mechanism is unresolved.",
            "reader_after": "The mechanism follows from the control.",
            "why_it_matters": "This separates the competing explanations.",
        },
        "story_candidates": [
            story("STY-0001", "selected", ["MOV-0001", "MOV-0002"]),
            story("STY-0002", "rejected", ["MOV-0001", "MOV-0002"]),
        ],
        "selected_story_id": "STY-0001",
        "single_candidate_reason": "",
        "claim_roles": {
            "foreground": {"claim_ids": ["CLM-0001"], "none_reason": ""},
            "supporting": {"claim_ids": [], "none_reason": "No supporting claim is needed."},
            "supplement": {"claim_ids": [], "none_reason": "No supplement claim is needed."},
            "cut": {"claim_ids": [], "none_reason": "No claim is cut."},
        },
        "argument_moves": [
            move("MOV-0001", 1, "MOV-0002"),
            move("MOV-0002", 2, ""),
        ],
        "visual_obligations": [
            {
                "id": "VIS-0001",
                "reader_task": "Compare the two mechanisms.",
                "takeaway": "Only the controlled mechanism changes.",
                "claim_ids": [],
                "preferred_form": "paired plot",
                "status": "planned",
                "waiver_reason": "",
                "figure_ids": [],
            }
        ],
        "results_hierarchy": {
            "document": "_paperops/model/editorial/results-hierarchy.yml",
            "item_ids": ["RHI-0001"],
        },
        "extensions": {},
        "metadata": {"updated_at": "2026-07-11"},
    }
    results: dict[str, object] = {
        "schema_version": 1,
        "items": [{"id": "RHI-0001"}],
    }
    return editorial, results


def findings_with_code(findings: list[object], code: str) -> list[object]:
    return [finding for finding in findings if getattr(finding, "code") == code]


class EditorialReferenceValidationTest(unittest.TestCase):
    def test_duplicate_story_move_and_visual_ids_are_reported(self) -> None:
        editorial, results = valid_documents()
        editorial["story_candidates"].append(copy.deepcopy(editorial["story_candidates"][0]))
        editorial["argument_moves"].append(copy.deepcopy(editorial["argument_moves"][0]))
        editorial["visual_obligations"].append(copy.deepcopy(editorial["visual_obligations"][0]))

        findings = validate_editorial_references(editorial, results)

        duplicates = findings_with_code(findings, "reference.duplicate")
        self.assertEqual(len(duplicates), 3)
        self.assertEqual(
            {finding.pointer for finding in duplicates},
            {"/story_candidates/2/id", "/argument_moves/2/id", "/visual_obligations/1/id"},
        )

    def test_dangling_local_references_are_reported_at_each_source(self) -> None:
        editorial, results = valid_documents()
        editorial["selected_story_id"] = "STY-missing"
        editorial["story_candidates"][0]["argument_move_ids"] = ["MOV-missing"]
        editorial["story_candidates"][0]["result_order"] = ["RHI-missing"]
        editorial["argument_moves"][0]["next_move_id"] = "MOV-missing"
        editorial["argument_moves"][0]["result_item_ids"] = ["RHI-missing"]
        editorial["results_hierarchy"]["item_ids"] = ["RHI-missing"]

        findings = validate_editorial_references(editorial, results)

        dangling = findings_with_code(findings, "reference.dangling")
        self.assertEqual(
            {finding.pointer for finding in dangling},
            {
                "/selected_story_id",
                "/story_candidates/0/argument_move_ids/0",
                "/story_candidates/0/result_order/0",
                "/argument_moves/0/next_move_id",
                "/argument_moves/0/result_item_ids/0",
                "/results_hierarchy/item_ids/0",
            },
        )

    def test_duplicate_target_does_not_create_secondary_dangling_finding(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"].append(copy.deepcopy(editorial["argument_moves"][0]))
        editorial["story_candidates"][0]["argument_move_ids"] = ["MOV-0001"]

        findings = validate_editorial_references(editorial, results)

        self.assertTrue(findings_with_code(findings, "reference.duplicate"))
        self.assertNotIn(
            "/story_candidates/0/argument_move_ids/0",
            {finding.pointer for finding in findings_with_code(findings, "reference.dangling")},
        )

    def test_duplicate_move_suppresses_ambiguous_graph_findings(self) -> None:
        editorial, results = valid_documents()
        editorial["claim_roles"]["foreground"] = {
            "claim_ids": [],
            "none_reason": "No foreground claim is assigned in this reference test.",
        }
        editorial["argument_moves"].append(copy.deepcopy(editorial["argument_moves"][0]))

        findings = validate_editorial_references(editorial, results)

        self.assertEqual({finding.code for finding in findings}, {"reference.duplicate"})

    def test_move_cycle_is_reported(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][1]["next_move_id"] = "MOV-0001"

        findings = validate_editorial_references(editorial, results)

        self.assertEqual(
            [finding.pointer for finding in findings_with_code(findings, "reference.cycle")],
            ["/argument_moves/1/next_move_id"],
        )

    def test_long_move_chain_does_not_depend_on_python_recursion_depth(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"] = [
            move(
                f"MOV-{index:04d}",
                index,
                f"MOV-{index + 1:04d}" if index < 1100 else "",
            )
            for index in range(1, 1101)
        ]

        findings = validate_editorial_references(editorial, results)

        self.assertFalse(findings_with_code(findings, "reference.cycle"))

    def test_move_position_gap_and_array_next_mismatch_are_reported_separately(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][1]["position"] = 3
        editorial["argument_moves"][0]["next_move_id"] = ""

        findings = validate_editorial_references(editorial, results)

        self.assertEqual(
            {finding.pointer for finding in findings_with_code(findings, "reference.order")},
            {"/argument_moves/1/position", "/argument_moves/0/next_move_id"},
        )

    def test_claim_and_figure_targets_are_deferred_as_info(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][0]["claim_ids"] = ["CLM-0002"]
        editorial["visual_obligations"][0]["claim_ids"] = ["CLM-0003"]
        editorial["visual_obligations"][0]["figure_ids"] = ["FIG-0001"]

        findings = validate_editorial_references(editorial, results)

        deferred = findings_with_code(findings, "reference.deferred")
        self.assertEqual(len(deferred), 4)
        self.assertTrue(all(finding.severity == "info" for finding in deferred))

    def test_absolute_and_traversal_results_paths_are_rejected(self) -> None:
        for document in (
            "/tmp/results.yml",
            "../results.yml",
            "model/../../results.yml",
            r"\outside\results.yml",
            r"C:outside\results.yml",
            r"\\server\share\results.yml",
        ):
            with self.subTest(document=document):
                editorial, results = valid_documents()
                editorial["results_hierarchy"]["document"] = document

                findings = validate_editorial_references(editorial, results)

                self.assertEqual(
                    [finding.pointer for finding in findings_with_code(findings, "reference.path")],
                    ["/results_hierarchy/document"],
                )

    def test_invalid_top_level_arrays_skip_dependent_reference_checks(self) -> None:
        cases = (
            ("story_candidates", "not an array", None),
            ("argument_moves", "not an array", None),
            ("visual_obligations", "not an array", None),
            ("claim_roles", "not an object", None),
            (None, None, "not an array"),
        )
        for editorial_field, invalid_value, invalid_result_items in cases:
            with self.subTest(editorial_field=editorial_field, results=invalid_result_items):
                editorial, results = valid_documents()
                editorial["claim_roles"]["foreground"] = {
                    "claim_ids": [],
                    "none_reason": "No foreground claim is assigned in this reference test.",
                }
                if editorial_field is not None:
                    editorial[editorial_field] = invalid_value
                if invalid_result_items is not None:
                    results["items"] = invalid_result_items

                findings = validate_editorial_references(editorial, results)

                self.assertEqual(findings, [])

    def test_invalid_nested_reference_arrays_are_skipped(self) -> None:
        editorial, results = valid_documents()
        editorial["story_candidates"][0]["argument_move_ids"] = "not an array"
        editorial["story_candidates"][0]["result_order"] = "not an array"
        editorial["argument_moves"][0]["claim_ids"] = "not an array"
        editorial["argument_moves"][0]["result_item_ids"] = "not an array"
        editorial["claim_roles"]["foreground"]["claim_ids"] = "not an array"
        editorial["visual_obligations"][0]["claim_ids"] = "not an array"
        editorial["visual_obligations"][0]["figure_ids"] = "not an array"
        editorial["results_hierarchy"]["item_ids"] = "not an array"

        findings = validate_editorial_references(editorial, results)

        self.assertEqual(findings, [])


class EditorialSemanticValidationTest(unittest.TestCase):
    def test_story_selection_requires_exactly_one_matching_selected_candidate(self) -> None:
        editorial, _ = valid_documents()
        editorial["story_candidates"][0]["status"] = "candidate"

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertTrue(findings_with_code(findings, "semantic.story_selection"))

    def test_selected_and_rejected_stories_require_their_reasons(self) -> None:
        editorial, _ = valid_documents()
        editorial["story_candidates"][0]["selection_reason"] = ""
        editorial["story_candidates"][1]["rejection_reason"] = ""

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(
            {
                finding.pointer
                for finding in findings_with_code(findings, "semantic.story_selection")
            },
            {
                "/story_candidates/0/selection_reason",
                "/story_candidates/1/rejection_reason",
            },
        )

    def test_single_story_requires_an_explanation(self) -> None:
        editorial, _ = valid_documents()
        editorial["story_candidates"] = [editorial["story_candidates"][0]]
        editorial["single_candidate_reason"] = ""

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(
            [finding.pointer for finding in findings_with_code(findings, "semantic.story_count")],
            ["/single_candidate_reason"],
        )

    def test_claim_roles_require_consistent_reasons_and_unique_assignment(self) -> None:
        editorial, _ = valid_documents()
        editorial["claim_roles"]["supporting"] = {"claim_ids": [], "none_reason": ""}
        editorial["claim_roles"]["supplement"] = {
            "claim_ids": ["CLM-0001"],
            "none_reason": "A reason must not accompany claims.",
        }

        findings = validate_editorial_semantics(editorial, strict=True)

        claim_role = findings_with_code(findings, "semantic.claim_role")
        self.assertEqual(
            {finding.pointer for finding in claim_role},
            {
                "/claim_roles/supporting/none_reason",
                "/claim_roles/supplement/none_reason",
                "/claim_roles/supplement/claim_ids/0",
            },
        )

    def test_move_requires_valid_stance_and_strict_reader_text(self) -> None:
        editorial, _ = valid_documents()
        editorial["argument_moves"][0]["stance"] = "observe"
        editorial["argument_moves"][0]["reader_question"] = ""
        editorial["argument_moves"][0]["assertion"] = "  "

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(
            {finding.pointer for finding in findings_with_code(findings, "semantic.move")},
            {
                "/argument_moves/0/stance",
                "/argument_moves/0/reader_question",
                "/argument_moves/0/assertion",
            },
        )

    def test_advisory_move_does_not_error_on_blank_reader_text(self) -> None:
        editorial, _ = valid_documents()
        editorial["argument_moves"][0]["reader_question"] = ""
        editorial["argument_moves"][0]["assertion"] = ""

        findings = validate_editorial_semantics(editorial, strict=False)

        self.assertFalse(findings_with_code(findings, "semantic.move"))

    def test_visual_waiver_requires_reason_and_satisfied_visual_requires_figure(self) -> None:
        editorial, _ = valid_documents()
        waived = editorial["visual_obligations"][0]
        waived["status"] = "waived"
        waived["waiver_reason"] = ""
        satisfied = copy.deepcopy(waived)
        satisfied["id"] = "VIS-0002"
        satisfied["status"] = "satisfied"
        satisfied["waiver_reason"] = "not relevant"
        satisfied["figure_ids"] = []
        editorial["visual_obligations"].append(satisfied)

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(
            {finding.pointer for finding in findings_with_code(findings, "semantic.visual")},
            {
                "/visual_obligations/0/waiver_reason",
                "/visual_obligations/1/figure_ids",
            },
        )

    def test_placeholder_is_warning_in_advisory_and_error_in_strict(self) -> None:
        editorial, _ = valid_documents()
        editorial["reader_transformation"]["reader_before"] = "未記入"

        advisory = validate_editorial_semantics(editorial, strict=False)
        strict = validate_editorial_semantics(editorial, strict=True)

        advisory_placeholder = findings_with_code(advisory, "semantic.placeholder")
        strict_placeholder = findings_with_code(strict, "semantic.placeholder")
        self.assertEqual([finding.severity for finding in advisory_placeholder], ["warning"])
        self.assertEqual([finding.severity for finding in strict_placeholder], ["error"])
        self.assertEqual(advisory_placeholder[0].pointer, "/reader_transformation/reader_before")

    def test_starter_gaps_are_advisory_warnings_but_strict_errors(self) -> None:
        editorial, _ = valid_documents()
        editorial["reader_transformation"] = {
            "reader_before": "未記入",
            "reader_after": "未記入",
            "why_it_matters": "未記入",
        }
        editorial["story_candidates"] = []
        editorial["selected_story_id"] = ""
        editorial["argument_moves"] = []
        editorial["visual_obligations"] = []
        editorial["results_hierarchy"]["item_ids"] = []
        editorial["metadata"]["updated_at"] = ""

        advisory = validate_editorial_semantics(editorial, strict=False)
        strict = validate_editorial_semantics(editorial, strict=True)

        self.assertTrue(findings_with_code(advisory, "semantic.placeholder"))
        self.assertFalse([finding for finding in advisory if finding.severity == "error"])
        self.assertTrue(findings_with_code(strict, "semantic.placeholder"))
        self.assertTrue(all(finding.severity == "error" for finding in strict))

    def test_extension_key_format_is_enforced(self) -> None:
        findings = validate_extension_keys(
            {
                "x-owner-valid_name": 1,
                "x-Owner-name": 2,
                "owner-name": 3,
                "x-owner": 4,
            }
        )

        self.assertEqual(
            {finding.pointer for finding in findings},
            {"/x-Owner-name", "/owner-name", "/x-owner"},
        )
        self.assertTrue(all(finding.code == "semantic.extension" for finding in findings))

    def test_semantics_include_extension_validation(self) -> None:
        editorial, _ = valid_documents()
        editorial["extensions"] = {"invalid": True}

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(
            [finding.pointer for finding in findings_with_code(findings, "semantic.extension")],
            ["/extensions/invalid"],
        )

    def test_invalid_semantic_collections_skip_dependent_findings(self) -> None:
        for field, invalid_value in (
            ("story_candidates", "not an array"),
            ("claim_roles", "not an object"),
            ("argument_moves", "not an array"),
            ("visual_obligations", "not an array"),
        ):
            with self.subTest(field=field):
                editorial, _ = valid_documents()
                editorial[field] = invalid_value
                if field == "story_candidates":
                    editorial["selected_story_id"] = ""

                findings = validate_editorial_semantics(editorial, strict=True)

                self.assertEqual(findings, [])

    def test_invalid_nested_semantic_arrays_are_skipped(self) -> None:
        editorial, _ = valid_documents()
        editorial["claim_roles"]["foreground"]["claim_ids"] = "not an array"
        editorial["visual_obligations"][0]["figure_ids"] = "not an array"

        findings = validate_editorial_semantics(editorial, strict=True)

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
