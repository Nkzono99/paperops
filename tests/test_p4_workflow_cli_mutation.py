from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from paperops.cli.main import build_parser, main


ROOT = Path(__file__).resolve().parents[1]
H = "sha256:" + "0" * 64


class WorkflowMutationCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)
        issue = {"schema_version": 1, "record_type": "workflow_issue", "id": "ISS-0001", "revision": 1, "status": "open", "dependencies": [], "approvals": [], "extensions": {}, "metadata": {"created_at": "", "updated_at": ""}, "severity": "major", "route": "editorial", "targets": [{"kind": "section", "id": "SEC-0001", "revision": 1, "hash": H}], "review_round_ref": "", "confidentiality": "public", "public_summary": "Reorder.", "closure_criteria": ["verified"], "blocking_dependency_refs": [], "impacts": [{"target_id": "SEC-0001", "target_type": "section", "expected_revision": 1, "expected_hash": H, "state": "resolved", "verification_refs": ["check:SEC-0001"]}], "route_history": [], "closure": {"decision": "pending", "reason": "", "verification_refs": []}, "escalation": {"level": "none", "reason": ""}}
        path = self.project / "_paperops/model/issues/workflow/ISS-0001.yml"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(issue) + "\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke(self, argv: list[str]) -> tuple[int, dict]:
        output = StringIO()
        with redirect_stdout(output):
            code = main(argv)
        return code, json.loads(output.getvalue())

    def test_parser_and_route_apply_rollback_lifecycle(self) -> None:
        args = build_parser().parse_args(["workflow", "issue", "route", "ISS-0001", "research", "--reason", "Evidence", "--path", str(self.project), "--json"])
        self.assertEqual(args.issue_action, "route")
        code, proposed = self.invoke(["workflow", "issue", "route", "ISS-0001", "research", "--reason", "Evidence", "--path", str(self.project), "--json"])
        self.assertEqual(code, 0)
        code, applied = self.invoke(["workflow", "apply", proposed["plan_id"], str(self.project), "--yes", "--json"])
        self.assertEqual(code, 0)
        code, status = self.invoke(["workflow", "issue", "status", "ISS-0001", "--path", str(self.project), "--json"])
        self.assertEqual(status["issues"][0]["route"], "research")
        code, rolled = self.invoke(["workflow", "rollback", applied["transaction_id"], str(self.project), "--yes", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(rolled["state"], "ROLLED_BACK")

    def test_apply_without_yes_is_rejected(self) -> None:
        code, proposed = self.invoke(["workflow", "issue", "route", "ISS-0001", "research", "--reason", "Evidence", "--path", str(self.project), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(main(["workflow", "apply", proposed["plan_id"], str(self.project)]), 2)


if __name__ == "__main__":
    unittest.main()
