from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "template/_paperops/defaults/schemas"


class WorkflowIssueSchemaTest(unittest.TestCase):
    def test_workflow_issue_is_closed_and_binds_typed_impacts(self) -> None:
        schema = json.loads((SCHEMA_DIR / "issue-workflow-issue.schema.json").read_text())
        document = {
            "schema_version": 1, "record_type": "workflow_issue", "id": "ISS-0001", "revision": 1,
            "status": "open", "dependencies": [], "approvals": [], "extensions": {},
            "metadata": {"created_at": "", "updated_at": ""}, "severity": "major",
            "route": "editorial", "targets": [{"kind": "section", "id": "SEC-0001", "revision": 1, "hash": "sha256:" + "0" * 64}],
            "review_round_ref": "RVW-0001", "confidentiality": "public", "public_summary": "Reorder the argument.",
            "closure_criteria": ["Architecture accepted"], "blocking_dependency_refs": [],
            "impacts": [{"target_id": "SEC-0001", "target_type": "section", "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64, "state": "open", "verification_refs": []}],
            "route_history": [], "closure": {"decision": "pending", "reason": "", "verification_refs": []},
            "escalation": {"level": "none", "reason": ""}
        }
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(document)), [])
        document["unknown"] = True
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(document)))

    def test_review_round_accepts_independent_issue_refs(self) -> None:
        schema = json.loads((SCHEMA_DIR / "issue-review-round.schema.json").read_text())
        self.assertIn("issue_refs", schema["properties"])
        registry = (SCHEMA_DIR / "registry.yml").read_text()
        self.assertIn("workflow_issue:", registry)


if __name__ == "__main__":
    unittest.main()
