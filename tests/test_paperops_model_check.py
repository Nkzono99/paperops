from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.helpers import ROOT, copy_template, run_python_script

from paperops_schema import load_document, semantic_hash


SCRIPT = ROOT / "template" / "scripts" / "check-paperops-models.py"


def story(story_id: str, status: str) -> dict[str, object]:
    return {
        "id": story_id,
        "label": f"Story {story_id}",
        "thesis": f"Thesis {story_id}",
        "result_order": ["RHI-0001"],
        "argument_move_ids": ["MOV-0001"],
        "status": status,
        "selection_reason": "Best supported." if status == "selected" else "",
        "rejection_reason": "Less direct." if status == "rejected" else "",
    }


def valid_documents() -> tuple[dict[str, object], dict[str, object]]:
    editorial: dict[str, object] = {
        "schema_version": 1,
        "model_id": "EDT-0001",
        "revision": 1,
        "reader_transformation": {
            "reader_before": "The mechanism is unresolved.",
            "reader_after": "The control identifies the mechanism.",
            "why_it_matters": "Competing explanations are separated.",
        },
        "story_candidates": [
            story("STY-0001", "selected"),
            story("STY-0002", "rejected"),
        ],
        "selected_story_id": "STY-0001",
        "single_candidate_reason": "",
        "claim_roles": {
            role: {"claim_ids": [], "none_reason": f"No {role} claim is assigned."}
            for role in ("foreground", "supporting", "supplement", "cut")
        },
        "argument_moves": [
            {
                "id": "MOV-0001",
                "position": 1,
                "stance": "assert",
                "reader_question": "What establishes the mechanism?",
                "assertion": "The controlled comparison establishes it.",
                "claim_ids": [],
                "result_item_ids": ["RHI-0001"],
                "next_move_id": "",
            }
        ],
        "visual_obligations": [
            {
                "id": "VIS-0001",
                "reader_task": "Compare the mechanisms.",
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
        "items": [
            {
                "id": "RHI-0001",
                "reader_question": "What changes?",
                "answer": "The controlled response changes.",
                "quantitative_evidence_and_unit_of_analysis": "Mean response per run.",
                "figure_table_role": "Main comparison.",
                "baseline_comparator_rationale": "The baseline isolates the control.",
                "consequence": "The mechanism is identified.",
                "next_item_id": "",
            }
        ],
    }
    return editorial, results


class PaperOpsModelCheckTest(unittest.TestCase):
    def write_documents(
        self,
        root: Path,
        editorial: dict[str, object],
        results: dict[str, object],
    ) -> tuple[Path, Path]:
        editorial_path = root / "editorial-model.yml"
        results_path = root / "results-hierarchy.yml"
        editorial_path.write_text(json.dumps(editorial, ensure_ascii=False), encoding="utf-8")
        results_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        return editorial_path, results_path

    def run_overrides(
        self,
        root: Path,
        editorial: dict[str, object],
        results: dict[str, object],
        *extra: object,
    ):
        editorial_path, results_path = self.write_documents(root, editorial, results)
        return run_python_script(
            SCRIPT,
            "--root",
            ROOT / "template",
            "--model",
            "editorial",
            "--document",
            editorial_path,
            "--results-document",
            results_path,
            *extra,
        )

    def test_starter_is_advisory_but_strict_fails_placeholders(self) -> None:
        advisory = run_python_script(SCRIPT, "--root", ROOT / "template")
        strict = run_python_script(SCRIPT, "--root", ROOT / "template", "--strict")

        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertIn("# paperops-model-check", advisory.stdout)
        self.assertRegex(advisory.stdout, r"(?s)## Warnings.*`\[semantic\.placeholder\] [^`]+`: ")
        self.assertEqual(strict.returncode, 1)
        self.assertRegex(strict.stdout, r"(?s)## Errors.*`\[semantic\.placeholder\] [^`]+`: ")
        for section in ("Errors", "Warnings", "Info"):
            self.assertIn(f"## {section}", advisory.stdout)

    def test_schema_failure_stops_dependent_phases(self) -> None:
        editorial, results = valid_documents()
        editorial["unknown_field"] = True
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(Path(tmp), editorial, results)

        self.assertEqual(result.returncode, 1)
        self.assertIn("[schema.additional] /unknown_field", result.stdout)
        self.assertNotIn("reference.dangling", result.stdout)
        self.assertNotIn("phase.prerequisite", result.stdout)

    def test_references_phase_reports_prerequisite_instead_of_schema_details(self) -> None:
        editorial, results = valid_documents()
        editorial["unknown_field"] = True
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("[phase.prerequisite]", result.stdout)
        self.assertNotIn("schema.additional", result.stdout)

    def test_references_phase_excludes_semantic_findings(self) -> None:
        editorial, results = valid_documents()
        editorial["story_candidates"] = [editorial["story_candidates"][0]]
        editorial["single_candidate_reason"] = ""
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.dangling", result.stdout)
        self.assertNotIn("semantic.story_count", result.stdout)

    def test_hash_phase_is_independent_and_keeps_normal_report_shape(self) -> None:
        editorial, results = valid_documents()
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "hash"
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("# paperops-model-check", result.stdout)
        self.assertNotIn("reference.dangling", result.stdout)
        self.assertNotIn("semantic.story_selection", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

    def test_checker_reports_non_json_extension_with_pointer_without_traceback(self) -> None:
        fixture_dir = ROOT / "tests/fixtures/editorial/mechanism-led"
        base_text = (fixture_dir / "editorial-model.yml").read_text(encoding="utf-8")
        cases = {
            "timestamp": ("x-test-date: 2026-07-11", "/extensions/x-test-date"),
            "set": ("x-test-set: !!set {one: null}", "/extensions/x-test-set"),
            "non-string-key": ("1: value", "/extensions"),
            "binary": ("x-test-binary: !!binary SGVsbG8=", "/extensions/x-test-binary"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, (extension_source, pointer) in cases.items():
                with self.subTest(name=name):
                    editorial_path = root / f"{name}.yml"
                    editorial_path.write_text(
                        base_text.replace(
                            "extensions: {}",
                            "extensions:\n  " + extension_source,
                        ),
                        encoding="utf-8",
                    )
                    result = run_python_script(
                        SCRIPT,
                        "--root", ROOT / "template", "--model", "editorial",
                        "--document", editorial_path,
                        "--results-document", fixture_dir / "results-hierarchy.yml",
                        "--phase", "hash",
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(f"[document.non_json] {pointer}", result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_deferred_claim_and_figure_references_are_info_only(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][0]["claim_ids"] = ["CLM-0001"]
        editorial["visual_obligations"][0]["figure_ids"] = ["FIG-0001"]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r"(?s)## Info.*reference\.deferred")
        errors_section = result.stdout.split("## Warnings", 1)[0]
        self.assertNotIn("reference.deferred", errors_section)

    def test_print_hash_requires_a_clean_single_model(self) -> None:
        editorial, results = valid_documents()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = self.run_overrides(root, editorial, results, "--print-hash")
            invalid_editorial = copy.deepcopy(editorial)
            invalid_editorial["unknown_field"] = True
            invalid = self.run_overrides(
                root, invalid_editorial, results, "--print-hash"
            )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertRegex(valid.stdout, r"^sha256:[0-9a-f]{64}\n?$")
        self.assertEqual(invalid.returncode, 1)
        self.assertNotRegex(invalid.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

        for phase_args in ((), ("--phase", "schema")):
            with self.subTest(phase_args=phase_args):
                starter = run_python_script(
                    SCRIPT,
                    "--root",
                    ROOT / "template",
                    "--model",
                    "editorial",
                    *phase_args,
                    "--print-hash",
                )
                self.assertEqual(starter.returncode, 1)
                self.assertIn("semantic.placeholder", starter.stdout)
                self.assertNotRegex(starter.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

    def test_print_hash_can_select_virtual_object_without_fabricated_revision(self) -> None:
        editorial, results = valid_documents()
        expected = semantic_hash(editorial["story_candidates"][0])
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp),
                editorial,
                results,
                "--print-hash",
                "--object-id",
                "STY-0001",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), expected)

    def test_missing_object_id_is_a_stable_finding(self) -> None:
        editorial, results = valid_documents()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp),
                editorial,
                results,
                "--print-hash",
                "--object-id",
                "STY-missing",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("[reference.dangling] /object-id", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_unregistered_known_model_is_a_stable_registry_finding(self) -> None:
        result = run_python_script(
            SCRIPT, "--root", ROOT / "template", "--model", "publication"
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("[registry.model] /", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_catalog_findings_are_partitioned_once_by_phase(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "paperops_model_checker_phase_test", SCRIPT
        )
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        try:
            spec.loader.exec_module(checker)
            local = (
                checker.ModelFinding("schema.required", "/record/id", "missing"),
                checker.ModelFinding("document.non_json", "/record", "invalid"),
                checker.ModelFinding(
                    "reference.orphan", "/records", "orphan", "warning"
                ),
                checker.ModelFinding("index.hash", "/records/0/expected_hash", "stale"),
                checker.ModelFinding("hash.non_json", "/record", "invalid hash"),
            )
            global_findings = (
                checker.ModelFinding("reference.duplicate", "/record/id", "duplicate"),
            )
            expected_local = {
                "all": [
                    "schema.required",
                    "document.non_json",
                    "reference.orphan",
                    "index.hash",
                    "hash.non_json",
                ],
                "schema": ["schema.required", "document.non_json"],
                "references": ["reference.orphan", "index.hash"],
                "hash": [
                    "schema.required",
                    "document.non_json",
                    "reference.orphan",
                    "index.hash",
                    "hash.non_json",
                ],
            }
            expected_global = {
                "all": ["reference.duplicate"],
                "schema": [],
                "references": ["reference.duplicate"],
                "hash": ["reference.duplicate"],
            }
            for phase in ("all", "schema", "references", "hash"):
                with self.subTest(phase=phase):
                    self.assertEqual(
                        [
                            finding.code
                            for finding in checker._catalog_findings_for_phase(
                                local, phase
                            )
                        ],
                        expected_local[phase],
                    )
                    self.assertEqual(
                        [
                            finding.code
                            for finding in checker._global_catalog_findings_for_phase(
                                global_findings, phase
                            )
                        ],
                        expected_global[phase],
                    )
        finally:
            sys.modules.pop(spec.name, None)

    def test_deduplication_preserves_multiple_orphans_and_models_at_same_pointer(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "paperops_model_checker_dedupe_test", SCRIPT
        )
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        try:
            spec.loader.exec_module(checker)
            first = checker.ModelFinding(
                "reference.orphan", "/records", "research orphan A"
            )
            second = checker.ModelFinding(
                "reference.orphan", "/records", "research orphan B"
            )
            third = checker.ModelFinding(
                "reference.orphan", "/records", "manuscript orphan A"
            )

            deduplicated = checker._deduplicate_findings(
                [first, first, second, third]
            )

            self.assertEqual(deduplicated, [first, second, third])
        finally:
            sys.modules.pop(spec.name, None)

    def test_record_schema_failure_blocks_references_but_schema_shows_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            schema_dir = project / "_paperops/defaults/schemas"
            registry_path = schema_dir / "registry.yml"
            registry = load_document(registry_path)
            (schema_dir / "claim.schema.json").write_text(
                json.dumps(
                    {
                        "type": "object",
                        "required": ["id", "record_type", "revision"],
                        "properties": {
                            "id": {"type": "string"},
                            "record_type": {"const": "claim"},
                            "revision": {"type": "integer"},
                        },
                        "additionalProperties": False,
                    }
                ),
                encoding="utf-8",
            )
            registry["models"]["manuscript"] = {
                "document_kind": "index",
                "schema": "model-index.schema.json",
                "schema_version": 1,
                "authority": "project-owned",
                "default_path": "_paperops/model/manuscript/index.yml",
                "hash_profile": "semantic-v1",
                "hash_excluded_paths": [],
                "record_sets": {
                    "claim": {
                        "schema": "claim.schema.json",
                        "path_prefix": "_paperops/model/manuscript/claims/",
                        "id_pattern": "^CLM-[0-9]{4,}$",
                        "hash_excluded_paths": [],
                    }
                },
                "dependency_profile": "dependency-v1",
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            record = {
                "id": "CLM-0001",
                "record_type": "claim",
                "revision": 1,
                "unexpected": True,
            }
            record_path = project / "_paperops/model/manuscript/claims/CLM-0001.yml"
            record_path.parent.mkdir(parents=True)
            record_path.write_text(json.dumps(record), encoding="utf-8")
            digest = semantic_hash(record)
            index_path = project / "_paperops/model/manuscript/index.yml"
            index_path.write_text(
                json.dumps(
                    {
                        "model_name": "manuscript",
                        "schema_version": 1,
                        "index_revision": 1,
                        "records": [
                            {
                                "id": "CLM-0001",
                                "record_type": "claim",
                                "document": "_paperops/model/manuscript/claims/CLM-0001.yml",
                                "expected_revision": 1,
                                "expected_hash": digest,
                            }
                        ],
                        "extensions": {},
                        "metadata": {"updated_at": "2026-07-11"},
                    }
                ),
                encoding="utf-8",
            )

            references = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root",
                project,
                "--model",
                "manuscript",
                "--phase",
                "references",
            )
            schema = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root",
                project,
                "--model",
                "manuscript",
                "--phase",
                "schema",
            )

        self.assertEqual(references.returncode, 1)
        self.assertIn("[phase.prerequisite] /", references.stdout)
        self.assertNotIn("schema.additional", references.stdout)
        self.assertEqual(schema.returncode, 1)
        self.assertIn(
            "[schema.additional] /records/0/document/unexpected", schema.stdout
        )

    def test_editorial_and_catalog_duplicate_is_rendered_once(self) -> None:
        editorial, results = valid_documents()
        duplicate = copy.deepcopy(editorial["story_candidates"][0])
        duplicate["label"] = "Distinct row with duplicate ID"
        duplicate["status"] = "rejected"
        duplicate["selection_reason"] = ""
        duplicate["rejection_reason"] = "Duplicate ID mutation."
        editorial["story_candidates"].append(duplicate)
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stdout.count("[reference.duplicate] /story_candidates/2/id"),
            1,
        )

    def test_index_model_cli_prints_registered_record_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            schema_dir = project / "_paperops/defaults/schemas"
            registry_path = schema_dir / "registry.yml"
            registry = load_document(registry_path)
            record_schema = {
                "type": "object",
                "required": ["id", "record_type", "revision", "metadata"],
                "properties": {
                    "id": {"const": "CLM-0001"},
                    "record_type": {"const": "claim"},
                    "revision": {"const": 1},
                    "metadata": {"type": "object"},
                },
                "additionalProperties": False,
            }
            (schema_dir / "claim.schema.json").write_text(
                json.dumps(record_schema), encoding="utf-8"
            )
            registry["models"]["manuscript"] = {
                "document_kind": "index",
                "schema": "model-index.schema.json",
                "schema_version": 1,
                "authority": "project-owned",
                "default_path": "_paperops/model/manuscript/index.yml",
                "hash_profile": "semantic-v1",
                "hash_excluded_paths": ["/metadata/updated_at"],
                "record_sets": {
                    "claim": {
                        "schema": "claim.schema.json",
                        "path_prefix": "_paperops/model/manuscript/claims/",
                        "id_pattern": "^CLM-[0-9]{4,}$",
                        "hash_excluded_paths": ["/metadata/updated_at"],
                    }
                },
                "dependency_profile": "dependency-v1",
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            record = {
                "id": "CLM-0001",
                "record_type": "claim",
                "revision": 1,
                "metadata": {"updated_at": "2026-07-11"},
            }
            digest = semantic_hash(record, excluded_paths=("/metadata/updated_at",))
            record_path = project / "_paperops/model/manuscript/claims/CLM-0001.yml"
            record_path.parent.mkdir(parents=True)
            record_path.write_text(json.dumps(record), encoding="utf-8")
            index_path = project / "_paperops/model/manuscript/index.yml"
            index_path.write_text(
                json.dumps(
                    {
                        "model_name": "manuscript",
                        "schema_version": 1,
                        "index_revision": 1,
                        "records": [
                            {
                                "id": "CLM-0001",
                                "record_type": "claim",
                                "document": "_paperops/model/manuscript/claims/CLM-0001.yml",
                                "expected_revision": 1,
                                "expected_hash": digest,
                            }
                        ],
                        "extensions": {},
                        "metadata": {"updated_at": "2026-07-11"},
                    }
                ),
                encoding="utf-8",
            )

            result = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root",
                project,
                "--model",
                "manuscript",
                "--print-hash",
                "--object-id",
                "CLM-0001",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), digest)

    def test_print_hash_runs_references_despite_semantics_phase(self) -> None:
        editorial, results = valid_documents()
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp),
                editorial,
                results,
                "--phase",
                "semantics",
                "--print-hash",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.dangling", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

    def test_print_hash_runs_schema_despite_references_phase(self) -> None:
        editorial, results = valid_documents()
        editorial["unknown_field"] = True
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp),
                editorial,
                results,
                "--phase",
                "references",
                "--print-hash",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("schema.additional", result.stdout)
        self.assertNotIn("phase.prerequisite", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

    def test_print_hash_allows_info_only_and_prints_one_line(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][0]["claim_ids"] = ["CLM-0001"]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "schema", "--print-hash"
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r"^sha256:[0-9a-f]{64}\n?$")

    def test_document_overrides_use_the_supplied_rhi_instead_of_starters(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["item_ids"] = ["RHI-custom"]
        editorial["story_candidates"][0]["result_order"] = ["RHI-custom"]
        editorial["story_candidates"][1]["result_order"] = ["RHI-custom"]
        editorial["argument_moves"][0]["result_item_ids"] = ["RHI-custom"]
        results["items"][0]["id"] = "RHI-custom"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(Path(tmp), editorial, results)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("semantic.placeholder", result.stdout)
        self.assertNotIn("reference.dangling", result.stdout)

    def test_normal_project_uses_embedded_project_relative_results_document(self) -> None:
        editorial, results = valid_documents()
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            alternate = project / "project-state" / "alternate-results.yml"
            alternate.parent.mkdir()
            results["items"][0]["id"] = "RHI-alternate"
            alternate.write_text(json.dumps(results), encoding="utf-8")
            editorial["results_hierarchy"]["document"] = "project-state/alternate-results.yml"
            editorial["results_hierarchy"]["item_ids"] = ["RHI-alternate"]
            for story_item in editorial["story_candidates"]:
                story_item["result_order"] = ["RHI-alternate"]
            editorial["argument_moves"][0]["result_item_ids"] = ["RHI-alternate"]
            default_results = project / "_paperops/model/editorial/results-hierarchy.yml"
            default_results.write_text(
                default_results.read_text(encoding="utf-8").replace("RHI-0001", "RHI-default"),
                encoding="utf-8",
            )
            editorial_path = project / "_paperops/model/editorial/editorial-model.yml"
            editorial_path.write_text(json.dumps(editorial), encoding="utf-8")

            result = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root", project, "--model", "editorial", "--phase", "references",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("reference.dangling", result.stdout)

    def test_document_override_resolves_embedded_results_next_to_fixture(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["document"] = "results-hierarchy.yml"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            editorial_path, _ = self.write_documents(root, editorial, results)
            result = run_python_script(
                SCRIPT,
                "--root", ROOT / "template", "--model", "editorial",
                "--document", editorial_path, "--phase", "references",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("phase.prerequisite", result.stdout)

    def test_missing_embedded_results_document_is_a_stable_reference_error(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["document"] = "missing-results.yml"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            editorial_path, _ = self.write_documents(root, editorial, results)
            result = run_python_script(
                SCRIPT,
                "--root", ROOT / "template", "--model", "editorial",
                "--document", editorial_path, "--phase", "references",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("[reference.document] /results_hierarchy/document", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_explicit_results_override_wins_and_reports_its_source(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["document"] = "missing-results.yml"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(Path(tmp), editorial, results, "--phase", "references")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[reference.document_source] /results_hierarchy/document", result.stdout)
        self.assertIn("--results-document", result.stdout)

    def test_embedded_results_document_controls_actual_rhi_binding(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["document"] = "bound-results.yml"
        editorial["results_hierarchy"]["item_ids"] = ["RHI-bound"]
        for story_item in editorial["story_candidates"]:
            story_item["result_order"] = ["RHI-bound"]
        editorial["argument_moves"][0]["result_item_ids"] = ["RHI-bound"]
        results["items"][0]["id"] = "RHI-bound"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            editorial_path = root / "editorial-model.yml"
            editorial_path.write_text(json.dumps(editorial), encoding="utf-8")
            (root / "bound-results.yml").write_text(json.dumps(results), encoding="utf-8")
            (root / "results-hierarchy.yml").write_text(
                json.dumps({**results, "items": [{**results["items"][0], "id": "RHI-wrong"}]}),
                encoding="utf-8",
            )
            result = run_python_script(
                SCRIPT, "--root", ROOT / "template", "--model", "editorial",
                "--document", editorial_path, "--phase", "references",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("reference.dangling", result.stdout)

    def test_editorial_document_override_does_not_fall_back_to_project_default_results(self) -> None:
        editorial, _ = valid_documents()
        editorial["results_hierarchy"]["item_ids"] = ["RHI-missing"]
        with tempfile.TemporaryDirectory() as tmp:
            editorial_path = Path(tmp) / "editorial-model.yml"
            editorial_path.write_text(
                json.dumps(editorial, ensure_ascii=False), encoding="utf-8"
            )
            result = run_python_script(
                SCRIPT,
                "--root",
                ROOT / "template",
                "--model",
                "editorial",
                "--phase",
                "references",
                "--document",
                editorial_path,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.document", result.stdout)
        self.assertNotIn("phase.prerequisite", result.stdout)

    def test_unknown_model_and_phase_are_argparse_usage_errors(self) -> None:
        for args in (("--model", "unknown"), ("--phase", "unknown")):
            with self.subTest(args=args):
                result = run_python_script(SCRIPT, "--root", ROOT / "template", *args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)

    def test_all_invokes_hash_and_converts_hash_failures_to_findings(self) -> None:
        spec = importlib.util.spec_from_file_location("paperops_model_checker_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        spec.loader.exec_module(checker)
        stdout = StringIO()
        stderr = StringIO()
        argv = [str(SCRIPT), "--root", str(ROOT / "template"), "--model", "editorial"]
        try:
            with patch.object(checker, "semantic_hash", side_effect=ValueError("hash.non_json: /: bad")):
                with patch.object(sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
                    code = checker.main()
        finally:
            sys.modules.pop(spec.name, None)

        self.assertEqual(code, 1)
        self.assertIn("[hash.non_json] /", stdout.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class EditorialHashMutationTest(unittest.TestCase):
    def test_all_semantic_editorial_mutations_change_hash_except_updated_at(self) -> None:
        fixture = ROOT / "tests/fixtures/editorial/mechanism-led/editorial-model.yml"
        baseline = load_document(fixture)
        exclusions = ("/metadata/updated_at",)
        baseline_hash = semantic_hash(baseline, excluded_paths=exclusions)

        mutations = {
            "schema version": lambda value: value.__setitem__("schema_version", 2),
            "model id": lambda value: value.__setitem__("model_id", "EDT-mutated"),
            "thesis": lambda value: value["story_candidates"][0].__setitem__("thesis", "Changed thesis."),
            "selected story": lambda value: value.__setitem__("selected_story_id", "STY-synthetic-control-mechanism-2"),
            "claim role": lambda value: value["claim_roles"]["foreground"]["claim_ids"].append("CLM-mutated"),
            "move order": lambda value: value["argument_moves"].reverse(),
            "Results item refs": lambda value: value["results_hierarchy"]["item_ids"].reverse(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(baseline)
                mutate(changed)
                self.assertNotEqual(
                    semantic_hash(changed, excluded_paths=exclusions), baseline_hash
                )

        timestamp_only = copy.deepcopy(baseline)
        timestamp_only["metadata"]["updated_at"] = "2099-01-01"
        self.assertEqual(
            semantic_hash(timestamp_only, excluded_paths=exclusions), baseline_hash
        )

    def test_copied_scaffold_preserves_starter_codes_and_severities(self) -> None:
        source = run_python_script(SCRIPT, "--root", ROOT / "template")
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            copied = run_python_script(
                target / "scripts" / "check-paperops-models.py", "--root", target
            )

        pattern = re.compile(r"`\[([^]]+)\] [^`]+`:.*", re.MULTILINE)

        def code_severity(report: str) -> set[tuple[str, str]]:
            current = ""
            found: set[tuple[str, str]] = set()
            for line in report.splitlines():
                if line.startswith("## "):
                    current = line[3:].lower().removesuffix("s")
                match = pattern.fullmatch(line.removeprefix("- "))
                if match:
                    found.add((match.group(1), current))
            return found

        self.assertEqual(source.returncode, 0, source.stderr)
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertEqual(code_severity(source.stdout), code_severity(copied.stdout))


if __name__ == "__main__":
    unittest.main()
