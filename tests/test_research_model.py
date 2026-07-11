from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPTS = ROOT / "template/scripts"
SCHEMAS = ROOT / "template/_paperops/defaults/schemas"
CHECKER = SCRIPTS / "check-paperops-models.py"
sys.path.insert(0, str(SCRIPTS))

from paperops_models import (  # noqa: E402
    CatalogObject,
    ObjectCatalog,
    validate_research_semantics,
)
from paperops_schema import load_document, load_registry, semantic_hash, validate_schema  # noqa: E402


HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")


def envelope(record_type: str, object_id: str, status: str = "draft") -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": record_type,
        "id": object_id,
        "revision": 1,
        "status": status,
        "dependencies": [],
        "approvals": [],
        "extensions": {},
        "metadata": {"updated_at": "2026-07-11"},
    }


def claim() -> dict[str, object]:
    return {
        **envelope("claim", "CLM-0001", "approved"),
        "statement": "The controlled comparison supports the bounded mechanism.",
        "scope": "Validated parameter regime.",
        "limitation": "No extrapolation outside the tested regime.",
        "not_claiming": ["Universal validity"],
        "result_refs": ["RES-0001"],
        "source_refs": ["SRC-0001"],
        "figure_refs": ["FIG-0001"],
        "manuscript_block_refs": ["BLK-0001"],
        "visual_obligation_refs": ["VIS-0001"],
        "no_figure_reason": "",
        "warrant": "The comparator isolates the tested effect.",
        "assumptions": ["ASM-0001"],
        "gate_id": "GATE-0001",
        "gate_status": "ready_to_write",
        "human_approval": "approved",
        "abstract_conclusion_allowed": True,
        "validation_history": [
            {"validation_id": "VAL-0001", "decision": "validated", "note": "Checked."}
        ],
        "upstream_feedback_refs": [],
    }


def gate() -> dict[str, object]:
    return {
        **envelope("scientific_gate", "GATE-0001"),
        "claim_id": "CLM-0001",
        "gate_decision": "ready_to_write",
        "required_checks": ["independence", "direct_comparator"],
        "blocking_feedback_refs": [],
        "analysis_request_refs": [],
        "central_assumptions": [
            {
                "id": "ASM-0001",
                "guarded_claim_refs": ["CLM-0001"],
                "artifact_role": "validated_solver_output",
                "solved": True,
                "bound_role": "none",
                "manuscript_block_refs": ["BLK-0001"],
                "status": "supported",
                "required_follow_up": "",
            }
        ],
        "claim_stress_tests": [
            {
                "id": "STRESS-0001",
                "claim_component": "mechanism",
                "stress_input": "alternative comparator",
                "stress_outcome": "bounded result persists",
                "strongest_allowed_wording": "supports",
                "must_not_claim": "proves universally",
                "nearest_caveat": "tested regime",
                "source_artifact_ids": ["ART-0001"],
            }
        ],
        "external_validation_gates": [
            {
                "id": "EXT-0001",
                "blocking_claim_ref": "CLM-0001",
                "required_external_evidence": "independent measurement",
                "allowed_wording": "simulation-supported",
                "must_not_claim": "experimentally verified",
                "route_ref": "AREQ-0001",
            }
        ],
        "path_criterion": "checked",
        "evidence_design": "checked",
        "approved_writing_scope": "Bounded mechanism statement.",
        "not_covered": ["Untested regimes"],
        "block_reason": "",
        "history": [{"event_id": "HIS-0001", "decision": "ready_to_write", "note": "Ready."}],
        "human_approval": "approved",
    }


def result() -> dict[str, object]:
    return {
        **envelope("result", "RES-0001", "validated"),
        "observation": "The response differs from the comparator.",
        "estimand": "Mean controlled response.",
        "unit_of_analysis": "Independent run.",
        "denominator": "All validated runs.",
        "independence_risk": "Shared initialization is reported.",
        "comparison": {"treatment": "case", "comparator": "control", "metric": "response", "direction_magnitude": "higher"},
        "metrics": ["response"],
        "quantity_contracts": [
            {
                "id": "QTY-0001",
                "value": "12/20",
                "denominator": "20 validated runs",
                "unit": "fraction",
                "unit_of_analysis": "run",
                "estimand": "success fraction",
                "aggregation": "count / total",
                "independence": "runs use independent seeds",
                "source_artifact_id": "ART-0001",
                "manuscript_block_refs": ["BLK-0001"],
            }
        ],
        "source_refs": ["SRC-0001"],
        "artifact_provenance_ids": ["artifact:ART-0001"],
        "workflow_id": "workflow:analysis-v1",
        "input_manifest_id": "artifact:MANIFEST-0001",
        "commit_id": "commit:abcdef0",
        "claim_refs": ["CLM-0001"],
        "claim_role": "core_evidence",
        "figure_refs": ["FIG-0001"],
        "manuscript_block_refs": ["BLK-0001"],
        "scope": "Validated regime.",
        "limitation": "Finite ensemble.",
        "route": "keep",
    }


def figure() -> dict[str, object]:
    return {
        **envelope("figure", "FIG-0001", "validated"),
        "figure_ref": "figure:main-1",
        "reader_task": "Compare treatment and control.",
        "takeaway": "The treatment differs within scope.",
        "claim_or_decision": "CLM-0001",
        "encoding": "paired plot",
        "scale_denominator": "same denominator",
        "uncertainty": "run distribution",
        "caption_scope": "validated regime only",
        "accessibility": "color and marker redundant",
        "acceptance_criteria": ["axes_checked"],
        "why_figure_not_text_table": "The comparison must be seen together.",
        "panel_story": ["control", "treatment"],
        "primary_comparison": "treatment versus control",
        "annotation_plan": "Mark the bounded difference.",
        "caption_plan": "State scope and denominator.",
        "render_size": "single_column",
        "runops_handoff_id": "opaque:RUNOPS-0001",
        "missing_action": "",
        "result_refs": ["RES-0001"],
        "claim_refs": ["CLM-0001"],
        "manuscript_block_refs": ["BLK-0001"],
        "visual_obligation_refs": ["VIS-0001"],
        "manuscript_role": "main",
        "design_review": {
            "reader_task": "checked", "takeaway_sentence": "checked",
            "claim_or_decision": "checked", "encoding_choice": "checked",
            "scale_and_denominator": "checked", "uncertainty_or_distribution": "checked",
            "annotation_caption": "checked", "color_accessibility": "checked",
            "runops_handoff": "checked", "acceptance_criteria": "checked",
        },
        "audit_checks": {
            "color_range": "checked", "decision_boundary_visible": "checked",
            "manuscript_reference": "checked", "current_manuscript_role_aligned": "checked",
            "axes": "checked", "denominator": "checked", "caption_scope": "checked",
            "path_criterion": "checked", "state_visualization": "checked",
            "evidence_design": "checked",
        },
        "route": "manuscript",
    }


def source() -> dict[str, object]:
    return {
        **envelope("source", "SRC-0001", "verified"),
        "source_kind": "literature",
        "citation_keys": ["example2026"],
        "verification_state": "verified",
        "promotion_decision": "source_card",
        "promotion_required_when": ["claim_boundary"],
        "promotion_reason": "Supports a manuscript boundary.",
        "claim_boundary": "No universal extrapolation.",
        "parameter_choice": "Comparator follows precedent.",
        "reviewer_objection": "Boundary is explicit.",
        "method_precedent": "Controlled comparison.",
        "claim_refs": ["CLM-0001"],
        "manuscript_block_refs": ["BLK-0001"],
        "related_work_role": "method precedent",
        "related_work_cluster": "controlled methods",
        "paper_roles": {
            "supports": "bounded claim", "contrasts": "uncontrolled baseline",
            "motivates": "comparison", "challenges": "universal wording",
        },
        "public_provenance_refs": ["doi:10.0000/example"],
    }


class ResearchModelTest(unittest.TestCase):
    def schema_findings(self, record_type: str, document: dict[str, object]):
        schema = load_document(SCHEMAS / f"research-{record_type}.schema.json")
        return validate_schema(document, schema)

    def catalog(self, documents: list[tuple[str, dict[str, object]]]) -> ObjectCatalog:
        objects: dict[str, CatalogObject] = {}
        for object_type, document in documents:
            object_id = str(document["id"])
            objects[object_id] = CatalogObject(
                object_id=object_id,
                object_type=object_type,
                model_name="research",
                document=document,
                revision=int(document["revision"]),
                object_hash=semantic_hash(document, excluded_paths=HASH_EXCLUSIONS),
                pointer=f"/{object_id}",
            )
        return ObjectCatalog(objects, ())

    def test_registry_atomically_adds_research_and_empty_starter_passes(self) -> None:
        registry = load_registry(ROOT / "template")
        self.assertEqual(
            set(registry.entries), {"editorial", "results_hierarchy", "research"}
        )
        entry = registry.entries["research"]
        self.assertEqual(entry.document_kind, "index")
        self.assertEqual(
            set(entry.record_sets), {"claim", "result", "figure", "source", "scientific_gate"}
        )
        for record_set in entry.record_sets.values():
            self.assertEqual(record_set.hash_excluded_paths, HASH_EXCLUSIONS)
        starter = load_document(entry.default_path)
        self.assertEqual(starter["records"], [])
        result = run_python_script(
            CHECKER,
            "--root",
            ROOT / "template",
            "--model",
            "research",
            "--phase",
            "all",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_record_families_accept_complete_typed_documents(self) -> None:
        documents = {
            "claim": claim(),
            "result": result(),
            "figure": figure(),
            "source": source(),
            "gate": gate(),
        }
        for record_type, document in documents.items():
            with self.subTest(record_type=record_type):
                self.assertEqual(self.schema_findings(record_type, document), [])

    def test_common_envelope_status_id_and_extension_boundaries_are_exact(self) -> None:
        cases = []
        documents = {
            "claim": claim(), "result": result(), "figure": figure(), "source": source(), "gate": gate()
        }
        for record_type, document in documents.items():
            for field in (
                "schema_version", "record_type", "id", "revision", "status",
                "dependencies", "approvals", "extensions", "metadata",
            ):
                missing = copy.deepcopy(document)
                del missing[field]
                cases.append((record_type, missing, "schema.required", f"/{field}"))
            unknown = copy.deepcopy(document)
            unknown["raw_path"] = "/private/run/output.dat"
            cases.append((record_type, unknown, "schema.additional", "/raw_path"))
            extension = copy.deepcopy(document)
            extension["extensions"] = {"x-lab-local-ref": "opaque:LOCAL-0001"}
            self.assertEqual(self.schema_findings(record_type, extension), [])
            bad_status = copy.deepcopy(document)
            bad_status["status"] = "unknown"
            cases.append((record_type, bad_status, "schema.enum", "/status"))
            bad_id = copy.deepcopy(document)
            bad_id["id"] = "INVALID-1"
            cases.append((record_type, bad_id, "schema.pattern", "/id"))
        approval_with_credential = claim()
        approval_with_credential["approvals"] = [
            {
                "approval_id": "APR-0001", "kind": "scientific_scope",
                "decision": "approved", "object_revision": 1,
                "object_hash": "sha256:" + "0" * 64, "actor": "human",
                "note": "", "credential": "forbidden",
            }
        ]
        cases.append(
            (
                "claim", approval_with_credential, "schema.additional",
                "/approvals/0/credential",
            )
        )
        for record_type, document, code, pointer in cases:
            with self.subTest(record_type=record_type, code=code, pointer=pointer):
                self.assertIn(
                    (code, pointer),
                    [(finding.code, finding.pointer) for finding in self.schema_findings(record_type, document)],
                )

    def test_quantity_contract_is_complete_and_ids_are_globally_unique(self) -> None:
        incomplete = result()
        del incomplete["quantity_contracts"][0]["denominator"]
        self.assertIn(
            ("schema.required", "/quantity_contracts/0/denominator"),
            [(finding.code, finding.pointer) for finding in self.schema_findings("result", incomplete)],
        )
        second = result()
        second["id"] = "RES-0002"
        findings = validate_research_semantics(
            self.catalog([("result", result()), ("result", second)])
        )
        self.assertIn("reference.duplicate", [finding.code for finding in findings])

    def test_dependency_and_approval_envelopes_reject_missing_snapshots_and_credentials(self) -> None:
        document = claim()
        subject_hash = semantic_hash(document, excluded_paths=HASH_EXCLUSIONS)
        document["dependencies"] = [
            {
                "target_id": "RES-0001",
                "relation": "supported_by",
                "expected_revision": 1,
                "expected_hash": "sha256:" + "1" * 64,
            }
        ]
        document["approvals"] = [
            {
                "approval_id": "APR-0001",
                "kind": "scientific_scope",
                "decision": "approved",
                "object_revision": 1,
                "object_hash": subject_hash,
                "actor": "human",
                "note": "Approved.",
            }
        ]
        self.assertEqual(self.schema_findings("claim", document), [])

        missing_snapshot = copy.deepcopy(document)
        del missing_snapshot["dependencies"][0]["expected_hash"]
        credential = copy.deepcopy(document)
        credential["approvals"][0]["email"] = "private@example.invalid"
        self.assertIn(
            ("schema.required", "/dependencies/0/expected_hash"),
            [
                (finding.code, finding.pointer)
                for finding in self.schema_findings("claim", missing_snapshot)
            ],
        )
        self.assertIn(
            ("schema.additional", "/approvals/0/email"),
            [
                (finding.code, finding.pointer)
                for finding in self.schema_findings("claim", credential)
            ],
        )

    def test_gate_decision_spelling_is_exact(self) -> None:
        invalid_gate = gate()
        invalid_gate["gate_decision"] = "ready-to-write"
        invalid_claim = claim()
        invalid_claim["gate_status"] = "ready-to-write"
        self.assertIn(
            ("schema.enum", "/gate_decision"),
            [
                (finding.code, finding.pointer)
                for finding in self.schema_findings("gate", invalid_gate)
            ],
        )
        self.assertIn(
            ("schema.enum", "/gate_status"),
            [
                (finding.code, finding.pointer)
                for finding in self.schema_findings("claim", invalid_claim)
            ],
        )

    def test_ready_gate_requires_current_scientific_scope_approval(self) -> None:
        approved_claim = claim()
        subject_hash = semantic_hash(approved_claim, excluded_paths=HASH_EXCLUSIONS)
        approved_claim["approvals"] = [
            {
                "approval_id": "APR-0001",
                "kind": "scientific_scope",
                "decision": "approved",
                "object_revision": 1,
                "object_hash": subject_hash,
                "actor": "human",
                "note": "Approved within scope.",
            }
        ]
        self.assertEqual(
            semantic_hash(approved_claim, excluded_paths=HASH_EXCLUSIONS), subject_hash
        )
        self.assertEqual(
            validate_research_semantics(
                self.catalog([("claim", approved_claim), ("scientific_gate", gate())])
            ),
            [],
        )
        missing = validate_research_semantics(
            self.catalog([("claim", claim()), ("scientific_gate", gate())])
        )
        self.assertIn("approval.missing", [finding.code for finding in missing])
        stale_claim = copy.deepcopy(approved_claim)
        stale_claim["approvals"][0]["object_revision"] = 0
        stale = validate_research_semantics(
            self.catalog([("claim", stale_claim), ("scientific_gate", gate())])
        )
        self.assertIn("approval.stale", [finding.code for finding in stale])

    def test_checker_dispatches_research_semantics_phase(self) -> None:
        spec = importlib.util.spec_from_file_location("research_checker_test", CHECKER)
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        stdout = StringIO()
        stderr = StringIO()
        argv = [
            str(CHECKER), "--root", str(ROOT / "template"),
            "--model", "research", "--phase", "semantics",
        ]
        try:
            spec.loader.exec_module(checker)
            injected = checker.ModelFinding(
                "semantic.research_probe", "/", "research semantics invoked"
            )
            with patch.object(
                checker, "validate_research_semantics", return_value=[injected]
            ):
                with patch.object(sys, "argv", argv):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        code = checker.main()
        finally:
            sys.modules.pop(spec.name, None)
        self.assertEqual(code, 1)
        self.assertIn("semantic.research_probe", stdout.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_gate_pairing_and_public_provenance_have_distinct_findings(self) -> None:
        paired_gate = gate()
        paired_gate["claim_id"] = "CLM-9999"
        invalid_source = source()
        invalid_source["public_provenance_refs"] = ["/private/capture.html"]
        findings = validate_research_semantics(
            self.catalog(
                [("claim", claim()), ("scientific_gate", paired_gate), ("source", invalid_source)]
            )
        )
        self.assertIn("semantic.gate_pair", [finding.code for finding in findings])
        self.assertIn("semantic.public_provenance", [finding.code for finding in findings])


if __name__ == "__main__":
    unittest.main()
