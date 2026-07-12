from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import yaml

from tests.helpers import run_cli

from paperops.change.planning import plan_change
from paperops.change.transaction import ChangeTransactionError, apply_change, recover_incomplete_changes, rollback_change
from paperops.model_state import read_model_states
from paperops.model_validation import ValidationFinding, ValidationResult
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

    def test_rollback_recovery_completes_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            tx = apply_change(project, plan.change_id, confirmed=True)
            with self.assertRaises(RuntimeError):
                rollback_change(project, tx, confirmed=True, fail_after=1)
            receipt = rollback_change(project, tx, confirmed=True)
            self.assertTrue(receipt.startswith("RBK-"))
            self.assertEqual(target.read_bytes(), before)

    def test_rollback_rejects_traversal_without_creating_outside_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project, _target, _plan = self.setup_plan(parent)
            with self.assertRaises(ChangeTransactionError):
                rollback_change(project, "CTX-../../escape", confirmed=True)
            self.assertFalse((parent / "escape").exists())

    def test_rollback_rejects_symlinked_transaction_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project, _target, plan = self.setup_plan(parent)
            transaction_id = "CTX-" + hashlib.sha256(plan.change_id.encode()).hexdigest()[:20]
            outside = parent / "outside"; outside.mkdir()
            transactions = project / ".paperops/changes/transactions"; transactions.mkdir(parents=True)
            (transactions / transaction_id).symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ChangeTransactionError, "unsafe"):
                rollback_change(project, transaction_id, confirmed=True)

    def test_recovery_completes_partially_written_rollback_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            transaction_id = apply_change(project, plan.change_id, confirmed=True)
            original_path = project / ".paperops/changes/transactions" / transaction_id / "journal.json"
            original = json.loads(original_path.read_text())
            receipt_id = "RBK-" + hashlib.sha256(transaction_id.encode()).hexdigest()[:20]
            receipt_dir = project / ".paperops/changes/transactions" / receipt_id; receipt_dir.mkdir()
            receipt = {"schema_version": 1, "transaction_id": receipt_id, "rollback_of": transaction_id, "state": "APPLYING", "entries": original["entries"]}
            receipt_path = receipt_dir / "journal.json"
            receipt_path.write_text(json.dumps(receipt)); receipt_path.chmod(0o600)
            publication = next(row for row in original["entries"] if row["identity"].endswith("publication-model.yml"))
            target.write_bytes(base64.b64decode(publication["pre"]))
            self.assertIn(receipt_id, recover_incomplete_changes(project))
            self.assertEqual(target.read_bytes(), before)
            recovered = json.loads((receipt_dir / "journal.json").read_text())
            self.assertEqual(recovered["state"], "COMMITTED")

    def test_apply_rejects_symlinked_lock_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project, target, plan = self.setup_plan(parent); before = target.read_bytes()
            outside = parent / "outside-lock"; outside.write_bytes(b"")
            lock = project / ".paperops/changes/lock"; lock.symlink_to(outside)
            with self.assertRaisesRegex(ChangeTransactionError, "lock"):
                apply_change(project, plan.change_id, confirmed=True)
            self.assertEqual(target.read_bytes(), before)

    def test_rollback_rejects_symlinked_journal_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project, target, plan = self.setup_plan(parent)
            transaction_id = apply_change(project, plan.change_id, confirmed=True); committed = target.read_bytes()
            journal = project / ".paperops/changes/transactions" / transaction_id / "journal.json"
            outside = parent / "outside-journal"; outside.write_bytes(journal.read_bytes())
            journal.unlink(); journal.symlink_to(outside)
            with self.assertRaisesRegex(ChangeTransactionError, "journal"):
                rollback_change(project, transaction_id, confirmed=True)
            self.assertEqual(target.read_bytes(), committed)

    def test_apply_rejects_new_candidate_warning_at_commit_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, target, plan = self.setup_plan(Path(tmp)); before = target.read_bytes()
            real_validation = __import__("paperops.change.transaction", fromlist=["run_model_validation"]).run_model_validation
            baseline = real_validation(project, "all", strict=False)
            warning = ValidationResult(1, True, "all", "all", (ValidationFinding("new.warning", "/candidate", "new", "warning"),), MappingProxyType(dict(plan.candidate_model_hashes)), 0)
            with patch("paperops.change.transaction.run_model_validation", side_effect=[baseline, warning]):
                with self.assertRaisesRegex(ChangeTransactionError, "warning"):
                    apply_change(project, plan.change_id, confirmed=True)
            self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
