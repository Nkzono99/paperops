from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import run_cli

from paperops.change.planning import plan_change
from paperops.change.transaction import ChangeTransactionError, apply_change, rollback_change
from paperops.model_state import read_model_states
from paperops.workflow_v2.mutation import semantic_hash


class ChangeTransactionTest(unittest.TestCase):
    def setup_plan(self, parent: Path):
        project = parent / "paper"
        code, _out, err = run_cli(["init", str(project)])
        self.assertEqual(code, 0, err)
        target = project / "_paperops/model/publication/publication-model.yml"
        document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
        document["revision"] = 1; document["venue"]["name"] = "Journal"
        request = parent / "request.yml"
        request.write_text(yaml.safe_dump({"schema_version": 1, "reason": "Select the publication venue.", "operations": [{"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-main", "expected_revision": 0, "expected_hash": digest, "document": document}]}, sort_keys=False))
        return project, target, plan_change(project, request)

    def test_apply_requires_confirmation_and_updates_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            with self.assertRaises(ChangeTransactionError):
                apply_change(project, plan.change_id)
            self.assertEqual(target.read_bytes(), before)
            tx = apply_change(project, plan.change_id, confirmed=True)
            self.assertTrue(tx.startswith("CTX-"))
            self.assertEqual(yaml.safe_load(target.read_text())["venue"]["name"], "Journal")
            self.assertEqual(read_model_states(project)["publication"].current_hash, plan.candidate_model_hashes["publication"])
            self.assertEqual(apply_change(project, plan.change_id, confirmed=True), tx)

    def test_source_drift_and_normal_failure_leave_old_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            target.write_text(target.read_text() + "# manual\n")
            with self.assertRaises(ChangeTransactionError):
                apply_change(project, plan.change_id, confirmed=True)
            target.write_bytes(before)
            with self.assertRaises(RuntimeError):
                apply_change(project, plan.change_id, confirmed=True, fail_after=1)
            self.assertEqual(target.read_bytes(), before)

    def test_rollback_creates_receipt_and_refuses_newer_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            tx = apply_change(project, plan.change_id, confirmed=True)
            target.write_text(target.read_text() + "# newer\n")
            with self.assertRaises(ChangeTransactionError):
                rollback_change(project, tx, confirmed=True)
            target.write_text(target.read_text().removesuffix("# newer\n"))
            receipt = rollback_change(project, tx, confirmed=True)
            self.assertTrue(receipt.startswith("RBK-"))
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(rollback_change(project, tx, confirmed=True), receipt)


if __name__ == "__main__":
    unittest.main()
