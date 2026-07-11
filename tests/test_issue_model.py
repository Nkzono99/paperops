from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPTS = ROOT / "template/scripts"
SCHEMAS = ROOT / "template/_paperops/defaults/schemas"
CHECKER = SCRIPTS / "check-paperops-models.py"
sys.path.insert(0, str(SCRIPTS))

from paperops_models import CatalogObject, ObjectCatalog, validate_issue_semantics  # noqa: E402
from paperops_schema import load_document, load_registry, semantic_hash, validate_schema  # noqa: E402


HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")


def envelope(record_type: str, object_id: str, status: str) -> dict[str, object]:
    return {
        "schema_version": 1, "record_type": record_type, "id": object_id,
        "revision": 1, "status": status, "dependencies": [], "approvals": [],
        "extensions": {}, "metadata": {"created_at": "2026-07-11", "updated_at": "2026-07-11"},
        "source": "human", "source_mode": "prompt", "severity": "major",
        "route": "evidence_loop", "targets": [{"kind": "manuscript_block", "id": "BLK-0001"}],
        "review_round_ref": "RVW-0001", "confidentiality": "internal_summary",
        "public_summary": "A bounded public summary.", "local_reference_id": "LOC-0001",
        "closure_criteria": ["Evidence and human decision are recorded."],
        "blocking_dependency_refs": [], "related_issue_refs": [],
        "related_card_refs": ["legacy:FB-0001"], "related_block_refs": ["BLK-0001"],
    }


def feedback() -> dict[str, object]:
    return {
        **envelope("feedback", "FB-0001", "open"),
        "issue_type": "overclaim", "upstream_routes": ["claim_scope_change"],
        "route_explanation": "The scope must match the validated regime.",
        "delegation": {"delegated_role": "evidence_auditor", "subagent_report_ref": "LOCAL-REPORT-0001", "integration_decision": "accepted_to_feedback_card"},
    }


def analysis_request(status: str = "reconciled") -> dict[str, object]:
    return {
        **envelope("analysis_request", "AREQ-0001", status),
        "requested_by": "FB-0001", "related_claim_refs": ["CLM-0001"],
        "related_result_refs": ["RES-0001"], "manuscript_refs": ["BLK-0001"],
        "figure_panels": ["FIG-0001:A"], "target_project_link_id": "LINK-0001",
        "requested_outputs": ["RES-0001"], "verification_axes": ["denominator"],
        "acceptance_criteria": {"artifact_refs": ["artifact:result-1"], "metric": "median", "estimand": "bounded effect", "denominator": "independent runs", "unit_of_analysis": "run", "independence_caveat": "Runs are the independent units.", "validated_scope": "registered cases", "not_covered": "unregistered regimes", "provenance_refs": ["commit:abcdef1"], "result_card_update_refs": ["legacy:RES-0001"]},
        "analysis_plan_frozen_commit": "commit:abcdef1", "data_not_seen_before_freeze": "confirmed",
        "planned_analysis": {"estimand": "bounded effect", "metric": "median", "denominator": "independent runs", "unit_of_analysis": "run", "comparison": "A versus B", "inclusion_exclusion": "registered cases", "decision_criteria": "report sign and interval", "stopping_condition": "registered sample complete", "outcome_neutral_qc": "conservation check"},
        "prediction": {"state": "predicted", "expected_sign": "positive", "expected_rank_or_range": "A > B", "uncertainty": "moderate", "basis_source_refs": ["SRC-0001"], "falsification_branch": "narrow the claim", "negative_null_route": "record negative result"},
        "replacement": {"xx_value_refs": ["QTY-0001"], "figure_panel_refs": ["FIG-0001:A"], "caption_scope": "bounded", "claim_scope": "bounded", "comments_to_remove": ["PREDICTED-RESULT", "SIM-REQUEST", "EXPECTATION-BASIS", "REPLACE-XX"]},
        "runops_handoff": {"runops_id": "RUNOPS-0001", "draft_snippet_ref": "LOCAL-SNIPPET-0001", "duplicate_check": "clear", "no_execution_guarantee": True},
        "execution_provenance": {"commit_ref": "commit:abcdef1", "run_id": "RUN-0001", "artifact_refs": ["artifact:result-1"], "artifact_hash_refs": ["sha256:" + "b" * 64], "result_refs": ["RES-0001"], "figure_refs": ["FIG-0001"], "archive_refs": ["doi:10.1234/example"]},
        "reconciliation": {"observed_result": "The bounded effect was positive.", "outcome": "confirmed", "deviations": "none", "updated_card_refs": ["legacy:RES-0001"], "gate_rerun": "completed", "human_signoff": "approved"},
    }


def writing_request() -> dict[str, object]:
    return {
        **envelope("writing_request", "WREQ-0001", "ready"),
        "requested_by": "FB-0001", "target_block_refs": ["BLK-0001"],
        "related_claim_refs": ["CLM-0001"], "related_feedback_refs": ["FB-0001"],
        "claim_evidence_constraints": {"claim_ref": "CLM-0001", "gate_status": "ready_to_write", "allowed_wording": "bounded association", "forbidden_overclaim": "universal causality"},
        "editing_policy": {"source_language": "ja", "mirror_policy": "ja_primary", "validation_refs": ["check:mirror"]},
    }


def response(status: str = "closed") -> dict[str, object]:
    document = {
        **envelope("response", "RSP-0001", status),
        "feedback_refs": ["FB-0001"], "resolution_routes": ["manuscript-change-closed"], "scope_changed": True,
        "response_plan": {"acknowledgement": "We agree the scope needed clarification.", "change_made": "The claim was bounded.", "evidence_analysis": "The reconciled analysis supports the bounded claim.", "manuscript_location_refs": ["BLK-0001"], "prose_explanation": "The response closes only after evidence and approval."},
        "closure_audit": {"closure_status": status, "criteria_met": True, "not_closed_reason": "", "next_required_evidence": [], "related_analysis_request_refs": ["AREQ-0001"], "open_human_decision_refs": [], "scope_change_approval_refs": ["APR-0001"]},
        "changed_claim_refs": ["CLM-0001"], "changed_block_refs": ["BLK-0001"],
        "changed_gate_refs": ["GATE-0001"], "changed_result_refs": ["RES-0001"],
        "changed_source_refs": ["SRC-0001"], "changed_figure_refs": ["FIG-0001"],
        "changed_request_refs": ["AREQ-0001"], "response_letter_summary": "The bounded change and evidence are recorded.",
    }
    if status == "closed":
        document["approvals"] = [{"approval_id": "APR-0001", "kind": "scope_expansion", "decision": "approved", "object_revision": 1, "object_hash": semantic_hash(document, excluded_paths=HASH_EXCLUSIONS), "actor": "human", "note": "Scope change approved."}]
    return document


def review_round() -> dict[str, object]:
    return {
        **envelope("review_round", "RVW-0001", "integrated"),
        "scope": "section", "artifact_refs": ["artifact:manuscript-v1"],
        "feedback_refs": ["FB-0001"], "review_profile": "public_reader",
        "round_summary": "The central claim needs a bounded scope.",
        "editorial_architecture_audit": {"story_spine": "coherent", "results_hierarchy": "complete", "discussion_functions": "complete", "claim_evidence_mismatch": "resolved", "highest_priority_route": "evidence_loop"},
        "delegation_ledger": [{"delegated_role": "evidence_auditor", "target_ref": "BLK-0001", "subagent_report_ref": "LOCAL-REPORT-0001", "route_recommendation": "evidence_loop", "integration_decision": "accepted_to_feedback_card", "decision_reason": "Actionable and in scope."}],
        "integration_decisions": [{"feedback_ref": "FB-0001", "decision": "accepted_to_feedback_card", "reason": "Requires tracked closure."}],
        "next_routes": ["integrate-writing-feedback"],
    }


DOCUMENTS = {"feedback": feedback, "analysis_request": analysis_request, "writing_request": writing_request, "response": response, "review_round": review_round}
STATUS_ENUMS = {
    "feedback": {"open", "routed", "addressed", "closed", "superseded"},
    "analysis_request": {"planned", "predicted", "running", "executed", "reconciled", "abandoned"},
    "writing_request": {"draft", "ready", "writing", "completed", "abandoned"},
    "response": {"draft", "first-pass-addressed", "partially-addressed", "scope-corrected-open", "analysis-open", "human-decision-open", "closed"},
    "review_round": {"draft", "reviewing", "integrating", "integrated", "closed"},
}


class IssueModelTest(unittest.TestCase):
    def schema_findings(self, record_type: str, document: dict[str, object]):
        schema = load_document(SCHEMAS / f"issue-{record_type.replace('_', '-')}.schema.json")
        return validate_schema(document, schema)

    def catalog(self, documents: list[dict[str, object]]) -> ObjectCatalog:
        objects = {}
        for document in documents:
            object_id = str(document["id"])
            objects[object_id] = CatalogObject(object_id, str(document["record_type"]), "issue", document, int(document["revision"]), semantic_hash(document, excluded_paths=HASH_EXCLUSIONS), f"/{object_id}")
        return ObjectCatalog(objects, ())

    def write_issue_record(self, project, document: dict[str, object]) -> None:
        record_type = str(document["record_type"])
        directory = {"feedback": "feedback", "analysis_request": "analysis", "writing_request": "writing", "response": "responses", "review_round": "rounds"}[record_type]
        relative = f"_paperops/model/issues/{directory}/{document['id']}.yml"
        record_path = project / relative
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        digest = semantic_hash(document, excluded_paths=HASH_EXCLUSIONS)
        index = {"model_name": "issue", "schema_version": 1, "index_revision": 1, "records": [{"id": document["id"], "record_type": record_type, "document": relative, "expected_revision": document["revision"], "expected_hash": digest}], "extensions": {}, "metadata": {"updated_at": "2026-07-11"}}
        (project / "_paperops/model/issues/index.yml").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_registry_stages_issue_as_fifth_entry_with_all_record_families(self) -> None:
        registry = load_registry(ROOT / "template")
        self.assertEqual(set(registry.entries), {"editorial", "results_hierarchy", "research", "manuscript", "issue"})
        entry = registry.entries["issue"]
        self.assertEqual(set(entry.record_sets), set(DOCUMENTS))
        self.assertEqual(entry.authority, "project-owned")
        self.assertEqual(entry.dependency_profile, "dependency-v1")

    def test_empty_issue_starter_is_schema_valid(self) -> None:
        entry = load_registry(ROOT / "template").entries["issue"]
        document = load_document(ROOT / "template/_paperops/model/issues/index.yml")
        self.assertEqual(document["records"], [])
        self.assertEqual(validate_schema(document, load_document(entry.schema_path)), [])

    def test_every_typed_payload_and_shared_envelope_is_schema_valid(self) -> None:
        shared = {"source", "source_mode", "severity", "route", "targets", "review_round_ref", "confidentiality", "public_summary", "local_reference_id", "closure_criteria", "blocking_dependency_refs", "related_issue_refs", "related_card_refs", "related_block_refs"}
        for record_type, factory in DOCUMENTS.items():
            with self.subTest(record_type=record_type):
                document = factory()
                self.assertEqual(self.schema_findings(record_type, document), [])
                schema = load_document(SCHEMAS / f"issue-{record_type.replace('_', '-')}.schema.json")
                self.assertTrue(shared.issubset(schema["required"]))

    def test_targets_preserve_legacy_kind_and_id_for_every_family(self) -> None:
        for record_type, factory in DOCUMENTS.items():
            with self.subTest(record_type=record_type):
                document = factory()
                self.assertEqual(document["targets"], [{"kind": "manuscript_block", "id": "BLK-0001"}])
                self.assertEqual(self.schema_findings(record_type, document), [])
                legacy_string = copy.deepcopy(document); legacy_string["targets"] = ["BLK-0001"]
                self.assertIn("schema.type", {f.code for f in self.schema_findings(record_type, legacy_string)})

    def test_analysis_acceptance_criteria_preserves_every_legacy_field_family(self) -> None:
        criteria = analysis_request()["acceptance_criteria"]
        self.assertEqual(set(criteria), {"artifact_refs", "metric", "estimand", "denominator", "unit_of_analysis", "independence_caveat", "validated_scope", "not_covered", "provenance_refs", "result_card_update_refs"})
        self.assertEqual(self.schema_findings("analysis_request", analysis_request()), [])
        missing = analysis_request(); del missing["acceptance_criteria"]["independence_caveat"]
        self.assertIn(("schema.required", "/acceptance_criteria/independence_caveat"), [(f.code, f.pointer) for f in self.schema_findings("analysis_request", missing)])

    def test_status_common_envelope_extension_and_dependency_contracts_are_exact(self) -> None:
        envelope_fields = {"schema_version", "record_type", "id", "revision", "status", "dependencies", "approvals", "extensions", "metadata"}
        for record_type, factory in DOCUMENTS.items():
            with self.subTest(record_type=record_type):
                document = factory()
                schema = load_document(SCHEMAS / f"issue-{record_type.replace('_', '-')}.schema.json")
                self.assertEqual(set(schema["properties"]["status"]["enum"]), STATUS_ENUMS[record_type])
                for field in envelope_fields:
                    missing = copy.deepcopy(document); del missing[field]
                    self.assertIn(("schema.required", f"/{field}"), [(f.code, f.pointer) for f in self.schema_findings(record_type, missing)])
                valid = copy.deepcopy(document); valid["extensions"] = {"x-lab-issue-note": "opaque:value"}
                self.assertEqual(self.schema_findings(record_type, valid), [])
                self.assertNotIn("semantic.extension", {f.code for f in validate_issue_semantics(self.catalog([valid]))})
                invalid = copy.deepcopy(document); invalid["extensions"] = {"invalid": True}
                self.assertIn("semantic.extension", {f.code for f in validate_issue_semantics(self.catalog([invalid]))})
                virtual = copy.deepcopy(document); virtual["dependencies"] = [{"target_id": "MOV-0001", "relation": "guided_by", "expected_hash": "sha256:" + "a" * 64}]
                self.assertEqual(self.schema_findings(record_type, virtual), [])
                missing_hash = copy.deepcopy(virtual); del missing_hash["dependencies"][0]["expected_hash"]
                self.assertIn(("schema.required", "/dependencies/0/expected_hash"), [(f.code, f.pointer) for f in self.schema_findings(record_type, missing_hash)])

    def test_unknown_raw_text_absolute_paths_and_credentials_are_rejected(self) -> None:
        raw = feedback(); raw["raw_reviewer_text"] = "confidential correspondence"
        self.assertIn("schema.additional", {f.code for f in self.schema_findings("feedback", raw)})
        for value in ("/home/user/reviewer.txt", "C:\\Users\\reviewer.txt", "token=secret"):
            with self.subTest(value=value):
                candidate = feedback(); candidate["public_summary"] = value
                self.assertIn("semantic.confidentiality", {f.code for f in validate_issue_semantics(self.catalog([candidate]))})

    def test_embedded_private_text_is_rejected_at_stable_public_summary_pointer(self) -> None:
        private_values = (
            "Reviewer file is /srv/private/reviewer/comment.txt and must stay local.",
            "Reviewer file is /reviewer.txt and must stay local.",
            "Reviewer file is ../private/file and must stay local.",
            "Reviewer scratch is /tmp and must stay local.",
            "Reviewer file is C:\\Users\\reviewer\\comment.txt and must stay local.",
            "Reviewer file is C:/Users/reviewer/comment.txt and must stay local.",
            "Local source file:///tmp/comment.txt must stay local.",
            "Remote source ssh://private.example/path must stay local.",
            "Remote source sftp://private.example/path must stay local.",
            "Authorization: Bearer abc.def.ghi",
            "Authorization: Basic YWxhZGRpbjpvcGVuc2VzYW1l",
            "The api key is abc123.", "API_KEY: abc123", "api-key=abc123",
            "The password is hunter2.", "The secret is 's3cr3t'.",
            'The credential is "abc123XYZ".', "The api key is `opaque-value`.",
            "The token is abc123.", "token: abc123", "token=abc123",
            "The access token is split.", "The auth token is split.",
            "The bearer token is split.", "The refresh token is split.",
            "The session token is split.", "The id token is split.",
            "-----BEGIN PRIVATE KEY----- secret material -----END PRIVATE KEY-----",
        )
        for value in private_values:
            with self.subTest(value=value):
                candidate = feedback(); candidate["public_summary"] = value
                findings = validate_issue_semantics(self.catalog([candidate]))
                self.assertIn(("semantic.confidentiality", "/FB-0001/public_summary"), [(f.code, f.pointer) for f in findings])

    def test_public_identifiers_and_ordinary_summary_have_no_privacy_false_positive(self) -> None:
        public_values = (
            "Public evidence is at https://example.org/results and doi:10.1234/example; the bounded token count is reported.",
            "The token is split by the tokenizer before the count is reported.",
            "The token is conserved across the analysis.",
            "The secret is not inferred from public data.",
            "The credential is described without storing a value.",
            "The API key is discussed but not recorded.",
        )
        for value in public_values:
            with self.subTest(value=value):
                candidate = feedback(); candidate["public_summary"] = value
                self.assertNotIn("semantic.confidentiality", {f.code for f in validate_issue_semantics(self.catalog([candidate]))})

    def test_executed_requires_output_references(self) -> None:
        candidate = analysis_request("executed")
        candidate["execution_provenance"]["artifact_refs"] = []
        candidate["execution_provenance"]["result_refs"] = []
        candidate["execution_provenance"]["figure_refs"] = []
        self.assertIn("semantic.execution_outputs", {f.code for f in validate_issue_semantics(self.catalog([candidate]))})

    def test_reconciled_requires_reconciliation_and_human_signoff(self) -> None:
        for field, value in (("observed_result", ""), ("human_signoff", "pending")):
            with self.subTest(field=field):
                candidate = analysis_request(); candidate["reconciliation"][field] = value
                self.assertIn("semantic.reconciliation", {f.code for f in validate_issue_semantics(self.catalog([candidate]))})

    def test_closed_response_rejects_open_analysis_and_human_decision_independently(self) -> None:
        open_request = analysis_request("running")
        closed = response()
        codes = {f.code for f in validate_issue_semantics(self.catalog([open_request, closed]))}
        self.assertIn("semantic.response_open_request", codes)
        human = response(); human["closure_audit"]["open_human_decision_refs"] = ["DEC-0001"]
        self.assertIn("semantic.response_human_decision", {f.code for f in validate_issue_semantics(self.catalog([human]))})

    def test_closed_response_cannot_bypass_open_request_through_dependencies(self) -> None:
        open_request = analysis_request("running")
        closed = response()
        closed["closure_audit"]["related_analysis_request_refs"] = []
        closed["dependencies"] = [{"target_id": "AREQ-0001", "relation": "blocked_by", "expected_revision": 1, "expected_hash": semantic_hash(open_request, excluded_paths=HASH_EXCLUSIONS)}]
        findings = validate_issue_semantics(self.catalog([open_request, closed]))
        self.assertIn(("semantic.response_open_request", "/RSP-0001/dependencies/0/target_id"), [(f.code, f.pointer) for f in findings])

    def test_closed_response_requires_nonempty_criteria_and_no_blockers(self) -> None:
        empty = response(); empty["closure_criteria"] = []
        blocked = response(); blocked["blocking_dependency_refs"] = ["AREQ-0001"]
        self.assertIn(("semantic.response_closure", "/RSP-0001/closure_criteria"), [(f.code, f.pointer) for f in validate_issue_semantics(self.catalog([empty]))])
        self.assertIn(("semantic.response_closure", "/RSP-0001/blocking_dependency_refs"), [(f.code, f.pointer) for f in validate_issue_semantics(self.catalog([blocked]))])

    def test_closed_response_requires_closure_criteria_and_scope_approval(self) -> None:
        candidate = response(); candidate["closure_audit"]["criteria_met"] = False; candidate["closure_audit"]["scope_change_approval_refs"] = []
        codes = {f.code for f in validate_issue_semantics(self.catalog([candidate]))}
        self.assertIn("semantic.response_closure", codes)
        self.assertIn("approval.missing", codes)

        stale = response()
        stale["approvals"][0]["object_hash"] = "sha256:" + "0" * 64
        self.assertIn("approval.stale", {f.code for f in validate_issue_semantics(self.catalog([stale]))})

        wording_only = response()
        wording_only["scope_changed"] = False
        wording_only["closure_audit"]["scope_change_approval_refs"] = []
        self.assertNotIn("approval.missing", {f.code for f in validate_issue_semantics(self.catalog([wording_only]))})

    def test_predicted_unresolved_is_independent_of_response_closure(self) -> None:
        predicted = analysis_request("predicted")
        codes = {f.code for f in validate_issue_semantics(self.catalog([predicted]))}
        self.assertIn("semantic.predicted_unresolved", codes)
        predicted_finding = next(f for f in validate_issue_semantics(self.catalog([predicted])) if f.code == "semantic.predicted_unresolved")
        self.assertEqual(predicted_finding.severity, "warning")
        self.assertFalse(any(code.startswith("semantic.response_") for code in codes))

    def test_checker_dispatches_issue_semantics(self) -> None:
        result = run_python_script(CHECKER, "--root", ROOT / "template", "--model", "issue", "--phase", "all")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checker_runs_issue_semantics_for_real_indexed_record_in_semantics_and_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            candidate = analysis_request("running")
            candidate["public_summary"] = "Reviewer artifact lives at /srv/private/reviewer.txt."
            self.write_issue_record(project, candidate)
            for phase in ("semantics", "all"):
                with self.subTest(phase=phase):
                    result = run_python_script(CHECKER, "--root", project, "--model", "issue", "--phase", phase)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("[semantic.confidentiality] /records/0/public_summary", result.stdout)

    def test_schema_invalid_issue_record_blocks_semantics_without_secondary_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            candidate = feedback(); candidate["raw_reviewer_text"] = "/srv/private/reviewer.txt"
            self.write_issue_record(project, candidate)
            semantics = run_python_script(CHECKER, "--root", project, "--model", "issue", "--phase", "semantics")
            self.assertEqual(semantics.returncode, 1, semantics.stdout + semantics.stderr)
            self.assertIn("[phase.prerequisite] /", semantics.stdout)
            self.assertNotIn("semantic.confidentiality", semantics.stdout)
            self.assertNotIn("schema.additional", semantics.stdout)
            all_phases = run_python_script(CHECKER, "--root", project, "--model", "issue", "--phase", "all")
            self.assertEqual(all_phases.returncode, 1, all_phases.stdout + all_phases.stderr)
            self.assertIn("[schema.additional] /records/0/document/raw_reviewer_text", all_phases.stdout)
            self.assertNotIn("semantic.confidentiality", all_phases.stdout)
            self.assertNotIn("phase.prerequisite", all_phases.stdout)

    def test_complete_issue_catalog_has_no_semantic_findings(self) -> None:
        self.assertEqual(validate_issue_semantics(self.catalog([factory() for factory in DOCUMENTS.values()])), [])


if __name__ == "__main__":
    unittest.main()
