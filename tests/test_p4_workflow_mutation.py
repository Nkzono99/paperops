from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import os
from pathlib import Path

from paperops.workflow_v2.approvals import inspect_approvals, plan_approval_decision
from paperops.workflow_v2.issues import inspect_issues, plan_issue_close, plan_issue_reopen, plan_issue_route
from paperops.workflow_v2.transaction import execute_workflow_apply, execute_workflow_rollback
from paperops.workflow_v2.mutation import semantic_hash


ROOT = Path(__file__).resolve().parents[1]
H = "sha256:" + "0" * 64


class WorkflowMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)
        issue = {
            "schema_version": 1, "record_type": "workflow_issue", "id": "ISS-0001", "revision": 1,
            "status": "open", "dependencies": [], "approvals": [], "extensions": {},
            "metadata": {"created_at": "", "updated_at": ""}, "severity": "major", "route": "editorial",
            "targets": [{"kind": "workflow_issue", "id": "ISS-0001", "revision": 1, "hash": H}], "review_round_ref": "",
            "confidentiality": "public", "public_summary": "Reorder the argument.", "closure_criteria": ["verified"],
            "blocking_dependency_refs": [], "impacts": [{"target_id": "ISS-0001", "target_type": "workflow_issue", "expected_revision": 1, "expected_hash": H, "state": "resolved", "verification_refs": ["check:ISS-0001"]}],
            "route_history": [], "closure": {"decision": "pending", "reason": "", "verification_refs": []},
            "escalation": {"level": "none", "reason": ""}
        }
        path = self.project / "_paperops/model/issues/workflow/ISS-0001.yml"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(issue) + "\n")
        index = {"model_name": "issue", "schema_version": 1, "index_revision": 1, "records": [{"id": "ISS-0001", "record_type": "workflow_issue", "document": "_paperops/model/issues/workflow/ISS-0001.yml", "expected_revision": 1, "expected_hash": semantic_hash(issue)}], "extensions": {}, "metadata": {"updated_at": ""}}
        (self.project / "_paperops/model/issues/index.yml").write_text(json.dumps(index) + "\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_issue_route_close_reopen_are_independent_and_transactional(self) -> None:
        route = plan_issue_route(self.project, "ISS-0001", "research", "Evidence changed")
        tx = execute_workflow_apply(self.project, route.plan_id, confirmed=True)
        self.assertEqual(inspect_issues(self.project, "ISS-0001").issues[0]["route"], "research")
        execute_workflow_rollback(self.project, tx, confirmed=True)
        self.assertEqual(inspect_issues(self.project, "ISS-0001").issues[0]["route"], "editorial")
        close = plan_issue_close(self.project, "ISS-0001", "Verified", ("check:ISS-0001",))
        execute_workflow_apply(self.project, close.plan_id, confirmed=True)
        self.assertEqual(inspect_issues(self.project, "ISS-0001").issues[0]["status"], "closed")
        reopen = plan_issue_reopen(self.project, "ISS-0001", "New evidence")
        execute_workflow_apply(self.project, reopen.plan_id, confirmed=True)
        self.assertEqual(inspect_issues(self.project, "ISS-0001").issues[0]["status"], "open")

    def test_owner_local_approval_is_bound_to_subject_hash(self) -> None:
        plan = plan_approval_decision(self.project, "ISS-0001", "scientific_scope", "approved", "Scope checked")
        execute_workflow_apply(self.project, plan.plan_id, confirmed=True)
        status = inspect_approvals(self.project, "ISS-0001")
        self.assertEqual(status.approvals[0]["decision"], "approved")
        self.assertEqual(status.approvals[0]["object_revision"], 1)
        self.assertTrue(status.approvals[0]["object_hash"].startswith("sha256:"))

    def test_apply_requires_confirmation_and_detects_drift(self) -> None:
        plan = plan_issue_route(self.project, "ISS-0001", "research", "Evidence changed")
        with self.assertRaises(ValueError):
            execute_workflow_apply(self.project, plan.plan_id, confirmed=False)
        issue = self.project / "_paperops/model/issues/workflow/ISS-0001.yml"
        issue.write_text(issue.read_text() + "\n")
        with self.assertRaises(ValueError):
            execute_workflow_apply(self.project, plan.plan_id, confirmed=True)

    def test_generated_workflow_namespace_cannot_be_a_symlink(self) -> None:
        namespace = self.project / ".paperops/workflow"
        if namespace.exists():
            shutil.rmtree(namespace)
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        namespace.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(outside, namespace)
        with self.assertRaises(ValueError):
            plan_issue_route(self.project, "ISS-0001", "research", "Evidence changed")


if __name__ == "__main__":
    unittest.main()
