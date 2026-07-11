from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from tests.helpers import ROOT, copy_template, run_python_script
from tests.test_research_model import claim as complete_research_claim


SCRIPTS = ROOT / "template/scripts"
SCHEMAS = ROOT / "template/_paperops/defaults/schemas"
CHECKER = SCRIPTS / "check-paperops-models.py"
sys.path.insert(0, str(SCRIPTS))

from paperops_models import (  # noqa: E402
    CatalogObject,
    ObjectCatalog,
    validate_manuscript_semantics,
    validate_research_semantics,
)
from paperops_schema import load_document, load_registry, semantic_hash, validate_schema  # noqa: E402


HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")
STATUS_ENUMS = {
    "section": {"unplanned", "planned", "compiled", "drafted", "verified", "stale"},
    "block": {"unplanned", "planned", "compiled", "drafted", "verified", "stale", "removed"},
}


def envelope(record_type: str, object_id: str, status: str) -> dict[str, object]:
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


def section() -> dict[str, object]:
    return {
        **envelope("section", "SEC-0001", "compiled"),
        "section_kind": "results",
        "ordered_block_ids": ["BLK-0001"],
        "contract_refs": ["contract:results"],
        "editorial_move_refs": ["MOV-0001"],
        "research_refs": ["CLM-0001", "RES-0001"],
        "source_language": "ja",
        "mirror_policy": "ja_primary",
        "compiled_manifest_ref": "manifest:SEC-0001-v1",
        "dependency_hash": "sha256:" + "1" * 64,
        "last_verified_dependency_hash": "sha256:" + "1" * 64,
    }


def block() -> dict[str, object]:
    return {
        **envelope("block", "BLK-0001", "compiled"),
        "section_id": "SEC-0001",
        "position": 1,
        "block_kind": "evidence",
        "reader_task": "Understand the bounded comparison.",
        "operation": "keep",
        "ja_tex_block_id": "results:block-1:ja",
        "en_tex_block_id": "results:block-1:en",
        "claim_refs": ["CLM-0001"],
        "result_refs": ["RES-0001"],
        "source_refs": ["SRC-0001"],
        "figure_refs": ["FIG-0001"],
        "citation_keys": ["example2026"],
        "compiled_from": {
            "compiler_version": "paperops-compiler-v1",
            "schema_versions": {"research": 1, "manuscript": 1},
            "input_ids": ["CLM-0001", "RES-0001"],
            "input_hashes": ["sha256:" + "2" * 64, "sha256:" + "3" * 64],
        },
        "dependency_hash": "sha256:" + "4" * 64,
        "last_verified_dependency_hash": "sha256:" + "4" * 64,
        "allowed_operations": ["keep", "compress", "move", "rewrite"],
        "forbidden_scope_expansion": ["Do not generalize beyond the validated regime."],
    }


def research_claim() -> dict[str, object]:
    document = {
        **envelope("claim", "CLM-0001", "approved"),
        "gate_id": "GATE-0001",
        "gate_status": "ready_to_write",
    }
    subject_hash = semantic_hash(document, excluded_paths=HASH_EXCLUSIONS)
    document["approvals"] = [{
        "approval_id": "APR-0001", "kind": "scientific_scope",
        "decision": "approved", "object_revision": 1,
        "object_hash": subject_hash, "actor": "human", "note": "Approved.",
    }]
    return document


def research_gate() -> dict[str, object]:
    return {
        **envelope("scientific_gate", "GATE-0001", "active"),
        "claim_id": "CLM-0001",
        "gate_decision": "ready_to_write",
    }


class ManuscriptModelTest(unittest.TestCase):
    def schema_findings(self, record_type: str, document: dict[str, object]):
        schema = load_document(SCHEMAS / f"manuscript-{record_type}.schema.json")
        return validate_schema(document, schema)

    def catalog(self, documents: list[tuple[str, str, dict[str, object]]]) -> ObjectCatalog:
        objects: dict[str, CatalogObject] = {}
        for model_name, object_type, document in documents:
            object_id = str(document["id"])
            exclusions = HASH_EXCLUSIONS if model_name in {"research", "manuscript"} else ()
            objects[object_id] = CatalogObject(
                object_id, object_type, model_name, document,
                int(document["revision"]),
                semantic_hash(document, excluded_paths=exclusions),
                f"/{object_id}",
            )
        return ObjectCatalog(objects, ())

    def complete_catalog(
        self,
        block_document: dict[str, object] | None = None,
    ) -> ObjectCatalog:
        return self.catalog([
            ("manuscript", "section", section()),
            ("manuscript", "block", block_document or block()),
            ("research", "claim", research_claim()),
            ("research", "scientific_gate", research_gate()),
            ("research", "result", {**envelope("result", "RES-0001", "validated")}),
            ("research", "source", {**envelope("source", "SRC-0001", "verified")}),
            ("research", "figure", {**envelope("figure", "FIG-0001", "validated")}),
        ])

    def test_registry_adds_manuscript_atomically_and_empty_starter_passes(self) -> None:
        registry = load_registry(ROOT / "template")
        self.assertEqual(
            set(registry.entries),
            {"editorial", "results_hierarchy", "research", "manuscript", "issue", "publication"},
        )
        entry = registry.entries["manuscript"]
        self.assertEqual(entry.document_kind, "index")
        self.assertEqual(set(entry.record_sets), {"section", "block"})
        self.assertTrue(all(rs.hash_excluded_paths == HASH_EXCLUSIONS for rs in entry.record_sets.values()))
        self.assertEqual(load_document(entry.default_path)["records"], [])
        result = run_python_script(
            CHECKER, "--root", ROOT / "template", "--model", "manuscript", "--phase", "all"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_section_and_block_cover_typed_field_families(self) -> None:
        self.assertEqual(self.schema_findings("section", section()), [])
        self.assertEqual(self.schema_findings("block", block()), [])
        for section_kind in (
            "abstract", "introduction", "methods", "results",
            "discussion", "conclusion", "supplement",
        ):
            with self.subTest(section_kind=section_kind):
                candidate = section()
                candidate["section_kind"] = section_kind
                self.assertEqual(self.schema_findings("section", candidate), [])

        prose = block()
        prose["prose"] = "This model must not become a prose authority."
        self.assertTrue(self.schema_findings("block", prose))

        block_schema = load_document(SCHEMAS / "manuscript-block.schema.json")
        operations = {
            "keep", "compress", "move", "merge", "split", "cut", "rewrite", "add",
        }
        self.assertEqual(set(block_schema["properties"]["operation"]["enum"]), operations)
        self.assertEqual(
            set(block_schema["properties"]["allowed_operations"]["items"]["enum"]),
            operations,
        )

    def test_unplanned_records_need_not_fabricate_compile_state(self) -> None:
        for status in ("unplanned", "planned"):
            with self.subTest(status=status):
                unplanned_section = section()
                unplanned_section["status"] = status
                unplanned_section["compiled_manifest_ref"] = ""
                unplanned_section["dependency_hash"] = ""
                unplanned_section["last_verified_dependency_hash"] = ""
                self.assertEqual(self.schema_findings("section", unplanned_section), [])

                unplanned_block = block()
                unplanned_block["status"] = status
                unplanned_block["compiled_from"] = None
                unplanned_block["dependency_hash"] = ""
                unplanned_block["last_verified_dependency_hash"] = ""
                unplanned_block["claim_refs"] = []
                unplanned_block["result_refs"] = []
                unplanned_block["source_refs"] = []
                unplanned_block["figure_refs"] = []
                self.assertEqual(self.schema_findings("block", unplanned_block), [])
                self.assertEqual(validate_manuscript_semantics(self.catalog([
                    ("manuscript", "section", unplanned_section),
                    ("manuscript", "block", unplanned_block),
                ])), [])

        planned_with_provenance = copy.deepcopy(unplanned_block)
        planned_with_provenance["status"] = "planned"
        planned_with_provenance["compiled_from"] = block()["compiled_from"]
        planned_with_provenance["claim_refs"] = ["CLM-0001"]
        findings = validate_manuscript_semantics(self.catalog([
            ("manuscript", "section", unplanned_section),
            ("manuscript", "block", planned_with_provenance),
        ]))
        self.assertIn("reference.dangling", [finding.code for finding in findings])

    def test_compiled_section_requires_manifest_and_both_dependency_hashes(self) -> None:
        for status in ("compiled", "drafted", "verified", "stale"):
            with self.subTest(status=status):
                candidate = section()
                candidate["status"] = status
                candidate["compiled_manifest_ref"] = ""
                candidate["dependency_hash"] = ""
                candidate["last_verified_dependency_hash"] = ""
                findings = validate_manuscript_semantics(
                    self.catalog([("manuscript", "section", candidate)])
                )
                self.assertIn(
                    ("semantic.compiled_from", "/SEC-0001/compiled_manifest_ref"),
                    [(finding.code, finding.pointer) for finding in findings],
                )
                self.assertIn(
                    ("dependency.missing", "/SEC-0001/dependency_hash"),
                    [(finding.code, finding.pointer) for finding in findings],
                )
                self.assertIn(
                    ("dependency.missing", "/SEC-0001/last_verified_dependency_hash"),
                    [(finding.code, finding.pointer) for finding in findings],
                )

    def test_compiled_block_states_require_provenance_and_both_hashes(self) -> None:
        for status in ("compiled", "drafted", "verified", "stale", "removed"):
            with self.subTest(status=status):
                candidate = block()
                candidate["status"] = status
                candidate["compiled_from"] = None
                candidate["dependency_hash"] = ""
                candidate["last_verified_dependency_hash"] = ""
                findings = validate_manuscript_semantics(self.catalog([
                    ("manuscript", "section", section()),
                    ("manuscript", "block", candidate),
                ]))
                pairs = {(finding.code, finding.pointer) for finding in findings}
                self.assertIn(("semantic.compiled_from", "/BLK-0001/compiled_from"), pairs)
                self.assertIn(("dependency.missing", "/BLK-0001/dependency_hash"), pairs)
                self.assertIn(
                    ("dependency.missing", "/BLK-0001/last_verified_dependency_hash"),
                    pairs,
                )

    def test_block_operation_must_be_allowed_for_that_block(self) -> None:
        candidate = block()
        candidate["operation"] = "cut"
        candidate["allowed_operations"] = ["keep", "rewrite"]
        findings = validate_manuscript_semantics(self.catalog([
            ("manuscript", "section", section()),
            ("manuscript", "block", candidate),
        ]))
        self.assertIn(
            ("semantic.operation", "/BLK-0001/operation"),
            [(finding.code, finding.pointer) for finding in findings],
        )

    def test_planned_block_with_compiled_lineage_requires_both_dependency_hashes(self) -> None:
        planned = block()
        planned["status"] = "planned"
        planned["dependency_hash"] = ""
        planned["last_verified_dependency_hash"] = ""
        findings = validate_manuscript_semantics(self.complete_catalog(planned))
        pairs = {(finding.code, finding.pointer) for finding in findings}
        self.assertIn(("dependency.missing", "/BLK-0001/dependency_hash"), pairs)
        self.assertIn(
            ("dependency.missing", "/BLK-0001/last_verified_dependency_hash"),
            pairs,
        )
        self.assertNotIn("semantic.compiled_from", {finding.code for finding in findings})

        planned["dependency_hash"] = "sha256:" + "4" * 64
        planned["last_verified_dependency_hash"] = "sha256:" + "4" * 64
        self.assertEqual(
            validate_manuscript_semantics(self.complete_catalog(planned)),
            [],
        )

    def test_status_enums_extensions_and_common_envelope_are_exact(self) -> None:
        for record_type, document in (("section", section()), ("block", block())):
            schema = load_document(SCHEMAS / f"manuscript-{record_type}.schema.json")
            self.assertEqual(set(schema["properties"]["status"]["enum"]), STATUS_ENUMS[record_type])
            for field in (
                "schema_version", "record_type", "id", "revision", "status",
                "dependencies", "approvals", "extensions", "metadata",
            ):
                changed = copy.deepcopy(document)
                del changed[field]
                self.assertIn(
                    ("schema.required", f"/{field}"),
                    [(f.code, f.pointer) for f in self.schema_findings(record_type, changed)],
                )
            valid_extension = copy.deepcopy(document)
            valid_extension["extensions"] = {"x-lab-manuscript-note": "opaque:value"}
            self.assertEqual(self.schema_findings(record_type, valid_extension), [])
            invalid_extension = copy.deepcopy(document)
            invalid_extension["extensions"] = {"invalid": True}
            findings = validate_manuscript_semantics(
                self.catalog([("manuscript", record_type, invalid_extension)])
            )
            self.assertIn("semantic.extension", [f.code for f in findings])

    def test_dependency_revision_is_optional_and_hash_required(self) -> None:
        for record_type, document in (("section", section()), ("block", block())):
            virtual = copy.deepcopy(document)
            virtual["dependencies"] = [{
                "target_id": "MOV-0001", "relation": "guided_by",
                "expected_hash": "sha256:" + "5" * 64,
            }]
            self.assertEqual(self.schema_findings(record_type, virtual), [])
            missing = copy.deepcopy(document)
            missing["dependencies"] = [{"target_id": "MOV-0001", "relation": "guided_by"}]
            self.assertIn(
                ("schema.required", "/dependencies/0/expected_hash"),
                [(f.code, f.pointer) for f in self.schema_findings(record_type, missing)],
            )

    def test_complete_catalog_passes_manuscript_semantics(self) -> None:
        self.assertEqual(validate_manuscript_semantics(self.complete_catalog()), [])

    def test_membership_and_positions_are_distinct(self) -> None:
        first = block()
        second = copy.deepcopy(first)
        second["id"] = "BLK-0002"
        second["position"] = 3
        second["section_id"] = "SEC-9999"
        broken_section = section()
        broken_section["ordered_block_ids"] = ["BLK-0002", "BLK-0001"]
        findings = validate_manuscript_semantics(self.catalog([
            ("manuscript", "section", broken_section),
            ("manuscript", "block", first),
            ("manuscript", "block", second),
        ]))
        codes = {finding.code for finding in findings}
        self.assertIn("semantic.section_membership", codes)
        self.assertIn("semantic.block_order", codes)

    def test_compiled_block_reports_approval_gate_compile_and_dependency_failures(self) -> None:
        unapproved = research_claim()
        unapproved["status"] = "draft"
        unapproved["approvals"] = []
        not_ready = research_gate()
        not_ready["gate_decision"] = "analysis_needed"
        stale_block = block()
        stale_block["last_verified_dependency_hash"] = "sha256:" + "9" * 64
        stale_block["compiled_from"]["input_hashes"] = []
        findings = validate_manuscript_semantics(self.catalog([
            ("manuscript", "section", section()),
            ("manuscript", "block", stale_block),
            ("research", "claim", unapproved),
            ("research", "scientific_gate", not_ready),
        ]))
        codes = {finding.code for finding in findings}
        self.assertIn("approval.missing", codes)
        self.assertIn("semantic.claim_not_writable", codes)
        self.assertIn("semantic.compiled_from", codes)
        self.assertIn("dependency.stale", codes)

    def test_current_rejected_claim_approval_is_missing_not_stale(self) -> None:
        rejected = research_claim()
        rejected["approvals"][-1]["decision"] = "rejected"
        catalog = self.catalog([
            ("manuscript", "section", section()),
            ("manuscript", "block", block()),
            ("research", "claim", rejected),
            ("research", "scientific_gate", research_gate()),
        ])
        findings = validate_manuscript_semantics(catalog)
        claim_findings = [
            finding for finding in findings
            if finding.pointer.endswith("/claim_refs/0")
        ]
        self.assertIn("approval.missing", [finding.code for finding in claim_findings])
        self.assertNotIn("approval.stale", [finding.code for finding in claim_findings])
        research_codes = {finding.code for finding in validate_research_semantics(catalog)}
        self.assertIn("approval.missing", research_codes)
        self.assertNotIn("approval.stale", research_codes)

    def test_compiled_block_reports_each_dangling_research_reference(self) -> None:
        findings = validate_manuscript_semantics(self.catalog([
            ("manuscript", "section", section()),
            ("manuscript", "block", block()),
        ]))
        dangling_pointers = {
            finding.pointer for finding in findings
            if finding.code == "reference.dangling"
        }
        for field in ("claim_refs", "result_refs", "source_refs", "figure_refs"):
            self.assertIn(f"/BLK-0001/{field}/0", dangling_pointers)

    def test_checker_dispatches_manuscript_semantics_with_research_catalog(self) -> None:
        spec = importlib.util.spec_from_file_location("manuscript_checker_test", CHECKER)
        assert spec is not None and spec.loader is not None
        checker = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = checker
        stdout, stderr = StringIO(), StringIO()
        argv = [str(CHECKER), "--root", str(ROOT / "template"), "--model", "manuscript", "--phase", "semantics"]
        try:
            spec.loader.exec_module(checker)
            injected = checker.ModelFinding("semantic.manuscript_probe", "/", "invoked")
            with patch.object(checker, "validate_manuscript_semantics", return_value=[injected]):
                with patch.object(sys, "argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
                    code = checker.main()
        finally:
            sys.modules.pop(spec.name, None)
        self.assertEqual(code, 1)
        self.assertIn("semantic.manuscript_probe", stdout.getvalue())

    def test_checker_requires_registered_research_for_manuscript_dependent_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            registry_path = project / "_paperops/defaults/schemas/registry.yml"
            registry = load_document(registry_path)
            registry["models"].pop("research")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            for phase in ("all", "semantics"):
                with self.subTest(phase=phase):
                    result = run_python_script(
                        project / "scripts/check-paperops-models.py",
                        "--root", project, "--model", "manuscript", "--phase", phase,
                    )
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("[phase.prerequisite] /", result.stdout)
                    self.assertIn("research", result.stdout)

    def _project_with_research_index_hash_and_orphan(self, tmp: str):
        project = copy_template(tmp)
        record = complete_research_claim()
        record_path = project / "_paperops/model/research/claims/CLM-0002.json"
        record_path.parent.mkdir(parents=True)
        record_path.write_text(json.dumps(record), encoding="utf-8")
        wrong_type = complete_research_claim()
        wrong_type["id"] = "RES-0002"
        wrong_type_path = project / "_paperops/model/research/results/RES-0002.json"
        wrong_type_path.parent.mkdir(parents=True)
        wrong_type_path.write_text(json.dumps(wrong_type), encoding="utf-8")
        index_path = project / "_paperops/model/research/index.yml"
        index = load_document(index_path)
        index["records"] = [
            {
                "id": "CLM-0002",
                "record_type": "claim",
                "document": "_paperops/model/research/claims/CLM-0002.json",
                "expected_revision": 2,
                "expected_hash": "sha256:" + "0" * 64,
            },
            {
                "id": "RES-0002",
                "record_type": "result",
                "document": "_paperops/model/research/results/RES-0002.json",
                "expected_revision": 1,
                "expected_hash": semantic_hash(
                    wrong_type, excluded_paths=HASH_EXCLUSIONS
                ),
            },
        ]
        index_path.write_text(json.dumps(index), encoding="utf-8")
        orphan = project / "_paperops/model/research/claims/CLM-9999.json"
        orphan.write_text("{}", encoding="utf-8")
        return project

    def test_manuscript_phases_propagate_research_catalog_findings_once(self) -> None:
        for phase in ("all", "semantics"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                project = self._project_with_research_index_hash_and_orphan(tmp)
                result = run_python_script(
                    project / "scripts/check-paperops-models.py",
                    "--root", project, "--model", "manuscript", "--phase", phase,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                for code in (
                    "index.hash", "index.id", "index.type", "index.revision",
                    "reference.orphan",
                ):
                    self.assertEqual(result.stdout.count(f"[{code}]"), 1)

    def test_supporting_research_orphan_keeps_advisory_and_strict_exit_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            orphan = project / "_paperops/model/research/claims/CLM-9999.json"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("{}", encoding="utf-8")
            advisory = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root", project, "--model", "manuscript", "--phase", "semantics",
            )
            strict = run_python_script(
                project / "scripts/check-paperops-models.py",
                "--root", project, "--model", "manuscript", "--phase", "semantics",
                "--strict",
            )
        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)
        self.assertEqual(advisory.stdout.count("[reference.orphan]"), 1)
        self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
        self.assertEqual(strict.stdout.count("[reference.orphan]"), 1)


if __name__ == "__main__":
    unittest.main()
