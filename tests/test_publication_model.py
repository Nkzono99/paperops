from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paperops_models import (  # noqa: E402
    CatalogObject,
    ObjectCatalog,
    validate_publication_semantics,
)
from paperops_schema import load_document, load_registry, semantic_hash, validate_schema  # noqa: E402


TEMPLATE = ROOT / "template"
SCHEMA = TEMPLATE / "_paperops/defaults/schemas/publication-model.schema.json"
STARTER = TEMPLATE / "_paperops/model/publication/publication-model.yml"
CHECKER = TEMPLATE / "scripts/check-paperops-models.py"
HASH = "sha256:" + "a" * 64


def dependency(target_id: str, *, revision: int | None = 1, digest: str = HASH) -> dict:
    value = {"target_id": target_id, "relation": "publication_input", "expected_hash": digest}
    if revision is not None:
        value["expected_revision"] = revision
    return value


def candidate() -> dict:
    return {
        "id": "CAND-0001",
        "revision": 1,
        "status": "gated",
        "manuscript_section_refs": ["SEC-0001"],
        "manuscript_block_refs": ["BLK-0001"],
        "claim_refs": ["CLM-0001"],
        "analysis_request_refs": ["AREQ-0001"],
        "required_response_refs": ["RSP-0001"],
        "review_round_ref": "RVW-0001",
        "source_commit": "commit:abcdef1",
        "gate_report_ref": "artifact:gate-report-1",
        "artifact_refs": ["artifact:manuscript-pdf"],
        "snapshot_dependencies": [
            dependency("CLM-0001"), dependency("BLK-0001"),
            dependency("AREQ-0001"), dependency("RSP-0001"),
        ],
    }


def publication() -> dict:
    current = candidate()
    return {
        "schema_version": 1,
        "model_id": "PUB-main",
        "revision": 1,
        "venue": {
            "venue_id": "VENUE-main",
            "name": "Example Journal",
            "requirements_profile": "profile:journal-v1",
            "requirements": [
                {"id": "REQ-0001", "status": "satisfied", "evidence_refs": ["artifact:gate-report-1"]}
            ],
        },
        "authoring": {
            "state": "reconciled",
            "living_manuscript_ref": "manuscript:living",
            "manuscript_revision": 7,
        },
        "submission_state": "submitted",
        "current_candidate": current,
        "current_round_id": "ROUND-0001",
        "rounds": [
            {
                "id": "ROUND-0001",
                "status": "submitted",
                "candidate_id": "CAND-0001",
                "candidate_revision": 1,
                "source_commit": "commit:abcdef1",
                "gate_report_ref": "artifact:gate-report-1",
                "artifact_refs": ["artifact:manuscript-pdf"],
                "snapshot_path": "submission/example/round-1",
                "snapshot_manifest_ref": "manifest:round-1",
                "snapshot_dependencies": copy.deepcopy(current["snapshot_dependencies"]),
                "review_round_ref": "RVW-0001",
                "response_package_refs": ["RSP-0001"],
                "immutable": True,
            }
        ],
        "submission_approvals": [
            {
                "approval_id": "APR-0001",
                "kind": "submission",
                "decision": "approved",
                "candidate_id": "CAND-0001",
                "candidate_revision": 1,
                "candidate_hash": semantic_hash(current),
                "actor": "human",
                "note": "Approved for submission.",
            }
        ],
        "extensions": {},
        "metadata": {"updated_at": "2026-07-11T00:00:00Z"},
    }


def obj(object_id: str, object_type: str, model_name: str, document: dict, digest: str = HASH) -> CatalogObject:
    return CatalogObject(
        object_id=object_id,
        object_type=object_type,
        model_name=model_name,
        document=document,
        revision=1,
        object_hash=digest,
        pointer=f"/{object_id}",
    )


def catalog() -> ObjectCatalog:
    claim_doc = {
        "status": "approved",
        "gate_status": "ready_to_write",
        "approvals": [{
            "kind": "scientific_scope", "decision": "approved",
            "object_revision": 1, "object_hash": HASH,
        }],
    }
    objects = {
        "CLM-0001": obj("CLM-0001", "claim", "research", claim_doc),
        "SEC-0001": obj("SEC-0001", "section", "manuscript", {"status": "verified"}),
        "BLK-0001": obj("BLK-0001", "block", "manuscript", {
            "status": "verified", "dependency_hash": HASH, "last_verified_dependency_hash": HASH,
        }),
        "AREQ-0001": obj("AREQ-0001", "analysis_request", "issue", {"status": "reconciled"}),
        "RSP-0001": obj("RSP-0001", "response", "issue", {"status": "closed"}),
        "RVW-0001": obj("RVW-0001", "review_round", "issue", {"status": "closed"}),
    }
    return ObjectCatalog(objects=objects, findings=())


class PublicationModelTest(unittest.TestCase):
    def schema_findings(self, document: dict) -> list:
        return validate_schema(document, load_document(SCHEMA))

    def codes(self, document: dict, objects: ObjectCatalog | None = None) -> set[str]:
        return {finding.code for finding in validate_publication_semantics(document, objects or catalog())}

    def test_registry_adds_sixth_aggregate_and_starter_is_valid(self) -> None:
        registry = load_registry(TEMPLATE)
        self.assertEqual(
            set(registry.entries),
            {"editorial", "results_hierarchy", "research", "manuscript", "issue", "publication"},
        )
        entry = registry.entries["publication"]
        self.assertEqual(entry.document_kind, "aggregate")
        self.assertEqual(entry.default_path, STARTER)
        self.assertEqual(self.schema_findings(load_document(STARTER)), [])

    def test_complete_document_covers_separate_axes_and_schema_contract(self) -> None:
        document = publication()
        self.assertEqual(self.schema_findings(document), [])
        self.assertEqual(document["authoring"]["state"], "reconciled")
        self.assertEqual(document["current_candidate"]["status"], "gated")
        self.assertEqual(document["rounds"][0]["status"], "submitted")

    def test_schema_rejects_unknown_fields_and_incomplete_round_snapshot(self) -> None:
        unknown = publication(); unknown["current_candidate"]["candidate_hash"] = HASH
        self.assertIn(("schema.any_of", "/current_candidate"), [(f.code, f.pointer) for f in self.schema_findings(unknown)])
        for field in ("source_commit", "gate_report_ref", "artifact_refs", "snapshot_path", "snapshot_manifest_ref", "snapshot_dependencies"):
            with self.subTest(field=field):
                missing = publication(); del missing["rounds"][0][field]
                self.assertIn(("schema.required", f"/rounds/0/{field}"), [(f.code, f.pointer) for f in self.schema_findings(missing)])

    def test_current_round_must_resolve_and_match_submission_state(self) -> None:
        missing = publication(); missing["current_round_id"] = "ROUND-9999"
        mismatch = publication(); mismatch["submission_state"] = "under_review"
        self.assertIn("reference.dangling", self.codes(missing))
        self.assertIn("semantic.round_state", self.codes(mismatch))

    def test_round_ids_and_snapshot_paths_are_unique(self) -> None:
        duplicate_id = publication(); duplicate_id["rounds"].append(copy.deepcopy(duplicate_id["rounds"][0]))
        duplicate_path = publication(); second = copy.deepcopy(duplicate_path["rounds"][0]); second["id"] = "ROUND-0002"; duplicate_path["rounds"].append(second)
        self.assertIn("reference.duplicate", self.codes(duplicate_id))
        self.assertIn("semantic.snapshot_path", self.codes(duplicate_path))
        escaped = publication(); escaped["rounds"][0]["snapshot_path"] = "submission/../private/round-1"
        self.assertIn("reference.path", self.codes(escaped))

    def test_gated_candidate_requires_current_submission_approval(self) -> None:
        missing = publication(); missing["submission_approvals"] = []
        stale = publication(); stale["submission_approvals"][0]["candidate_hash"] = HASH
        self.assertIn("approval.missing", self.codes(missing))
        self.assertIn("approval.stale", self.codes(stale))
        pending = publication(); pending["venue"]["requirements"][0]["status"] = "pending"
        self.assertIn("semantic.venue_requirement", self.codes(pending))

    def test_submitted_or_later_round_requires_immutable_marker(self) -> None:
        for status in ("submitted", "under_review", "resubmitted", "accepted", "rejected", "withdrawn"):
            with self.subTest(status=status):
                document = publication()
                document["rounds"][0]["status"] = status
                document["submission_state"] = status
                document["rounds"][0]["immutable"] = False
                self.assertIn("immutability.required", self.codes(document))

    def test_publication_rejects_unreconciled_or_predicted_analysis(self) -> None:
        for status in ("planned", "predicted", "running", "executed"):
            with self.subTest(status=status):
                objects = catalog()
                changed = dict(objects.objects); changed["AREQ-0001"] = obj("AREQ-0001", "analysis_request", "issue", {"status": status})
                self.assertIn("semantic.predicted_unresolved", self.codes(publication(), ObjectCatalog(changed, ())))
                dependency_only = publication(); dependency_only["current_candidate"]["analysis_request_refs"] = []
                dependency_only["rounds"][0]["snapshot_dependencies"] = copy.deepcopy(dependency_only["current_candidate"]["snapshot_dependencies"])
                dependency_only["submission_approvals"][0]["candidate_hash"] = semantic_hash(dependency_only["current_candidate"])
                self.assertIn("semantic.predicted_unresolved", self.codes(dependency_only, ObjectCatalog(changed, ())))

    def test_publication_rejects_unapproved_claim_and_stale_block(self) -> None:
        objects = catalog(); changed = dict(objects.objects)
        changed["CLM-0001"] = obj("CLM-0001", "claim", "research", {"status": "draft", "approvals": []})
        changed["BLK-0001"] = obj("BLK-0001", "block", "manuscript", {"status": "stale", "dependency_hash": HASH, "last_verified_dependency_hash": HASH})
        codes = self.codes(publication(), ObjectCatalog(changed, ()))
        self.assertIn("approval.missing", codes)
        self.assertIn("dependency.stale", codes)

        dependency_only = publication()
        dependency_only["current_candidate"]["claim_refs"] = []
        dependency_only["current_candidate"]["manuscript_block_refs"] = []
        dependency_only["rounds"][0]["snapshot_dependencies"] = copy.deepcopy(dependency_only["current_candidate"]["snapshot_dependencies"])
        dependency_only["submission_approvals"][0]["candidate_hash"] = semantic_hash(dependency_only["current_candidate"])
        dependency_codes = self.codes(dependency_only, ObjectCatalog(changed, ()))
        self.assertIn("approval.missing", dependency_codes)
        self.assertIn("dependency.stale", dependency_codes)

    def test_required_response_must_exist_and_be_closed(self) -> None:
        objects = catalog(); missing = dict(objects.objects); missing.pop("RSP-0001")
        open_response = dict(objects.objects); open_response["RSP-0001"] = obj("RSP-0001", "response", "issue", {"status": "draft"})
        self.assertIn("semantic.response_missing", self.codes(publication(), ObjectCatalog(missing, ())))
        self.assertIn("semantic.response_missing", self.codes(publication(), ObjectCatalog(open_response, ())))

    def test_living_manuscript_revision_does_not_change_snapshot_contract(self) -> None:
        original = publication(); revised = copy.deepcopy(original); revised["authoring"]["manuscript_revision"] += 1
        self.assertEqual(self.codes(original), set())
        self.assertEqual(self.codes(revised), set())

    def test_checker_dispatches_publication_semantics(self) -> None:
        result = run_python_script(CHECKER, "--root", TEMPLATE, "--model", "publication", "--phase", "all")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
