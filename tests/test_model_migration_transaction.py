from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template, run_cli
from tests.test_paperops_model_check import valid_documents

from paperops.model_migration.transaction import (
    InjectedTransactionFailure,
    execute_adoption,
    plan_adoption,
    recover_incomplete_transactions,
)
from paperops.model_state import manifest_bytes, read_model_states, write_model_states


class ModelMigrationTransactionTest(unittest.TestCase):
    def test_cli_adopt_requires_confirmation_and_repeat_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _transaction, old_target, _old_manifest = self.shadow(Path(tmp))
            code, raw, _ = run_cli(["model", "adopt", "publication", str(project), "--json"])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "transaction.confirmation")
            code, raw, err = run_cli(["model", "adopt", "publication", str(project), "--yes", "--json"])
            self.assertEqual(code, 0, err)
            result = json.loads(raw)
            self.assertTrue(result["ok"])
            self.assertNotEqual((project / "_paperops/model/publication/publication-model.yml").read_bytes(), old_target)
            self.assertEqual(read_model_states(project)["publication"].mode, "v2-authoritative")
            code, raw, _ = run_cli(["model", "adopt", "publication", str(project), "--yes", "--json"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(raw)["reused"])

            target = project / "_paperops/model/publication/publication-model.yml"
            target.write_text(target.read_text() + "# manual edit\n")
            code, raw, _ = run_cli(["model", "adopt", "publication", str(project), "--yes", "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "transaction.target_changed")

    def test_editorial_adoption_commits_results_companion_in_one_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            storyline = project / "_paperops/notes/views/storyline.md"
            storyline.write_text(
                "---\n"
                f"migration_editorial: {json.dumps(editorial)}\n"
                f"migration_results_hierarchy: {json.dumps(results)}\n"
                "---\n"
            )
            code, raw, err = run_cli(["model", "diff", "editorial", str(project), "--json"])
            self.assertEqual(code, 0, err)
            states = read_model_states(project)
            states["research"] = states["research"].__class__("research", "v2-authoritative", "sha256:" + "a" * 64, "", "model-bootstrap-0001")
            write_model_states(project, states)
            code, raw, err = run_cli(["model", "adopt", "editorial", str(project), "--yes", "--json"])
            self.assertEqual(code, 0, err)
            states = read_model_states(project)
            self.assertEqual(states["editorial"].mode, "v2-authoritative")
            self.assertEqual(states["results_hierarchy"].mode, "v2-authoritative")
            self.assertEqual(states["editorial"].last_adopt_transaction, states["results_hierarchy"].last_adopt_transaction)

    def test_dry_run_preserves_project_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _transaction, old_target, old_manifest = self.shadow(Path(tmp))
            code, raw, _ = run_cli(["model", "adopt", "publication", str(project), "--dry-run", "--json"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(raw)["ok"])
            self.assertEqual((project / "_paperops/model/publication/publication-model.yml").read_bytes(), old_target)
            self.assertEqual(manifest_bytes(project), old_manifest)

    def test_source_and_candidate_drift_stop_before_mutation(self) -> None:
        for drift in ("source", "candidate"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as tmp:
                project, transaction, old_target, old_manifest = self.shadow(Path(tmp))
                if drift == "source":
                    ledger = project / "_paperops/workflow/submission-ledger.yml"
                    ledger.write_text(ledger.read_text() + "# changed\n")
                    expected = "migration.source_changed"
                else:
                    candidate = project / ".paperops/migrations" / transaction / "candidate/_paperops/model/publication/publication-model.yml"
                    candidate.write_text(candidate.read_text() + "\n")
                    expected = "migration.candidate_changed"
                code, raw, _ = run_cli(["model", "adopt", "publication", str(project), "--yes", "--json"])
                self.assertEqual(code, 1)
                self.assertIn(expected, [item["code"] for item in json.loads(raw)["findings"]])
                self.assertEqual((project / "_paperops/model/publication/publication-model.yml").read_bytes(), old_target)
                self.assertEqual(manifest_bytes(project), old_manifest)

    def test_failures_at_journal_boundaries_recover_old_state(self) -> None:
        transitions = ("planned", "materialized", "validated", "snapshotted", "replacing", "committed")
        phases = tuple(f"before:{state}" for state in transitions) + (
            "after:planned",
            "after:materialized",
            "after:validated",
            "after:snapshotted",
            "after:replacing",
            "after:targets_replaced",
            "after:manifest_replaced",
        )
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                project, _transaction, old_target, old_manifest = self.shadow(Path(tmp))
                plan = plan_adoption(project, "publication")
                with self.assertRaises(InjectedTransactionFailure):
                    execute_adoption(plan, fail_at=phase)
                findings = recover_incomplete_transactions(project)
                self.assertNotIn("recovery.conflict", [item.code for item in findings])
                self.assertEqual((project / "_paperops/model/publication/publication-model.yml").read_bytes(), old_target)
                self.assertEqual(manifest_bytes(project), old_manifest)

    def test_unknown_manual_edit_after_replace_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _transaction, _old_target, _old_manifest = self.shadow(Path(tmp))
            plan = plan_adoption(project, "publication")
            with self.assertRaises(InjectedTransactionFailure):
                execute_adoption(plan, fail_at="after:targets_replaced")
            target = project / "_paperops/model/publication/publication-model.yml"
            target.write_text("manual unknown edit\n")
            findings = recover_incomplete_transactions(project)
            self.assertIn("recovery.conflict", [item.code for item in findings])
            self.assertEqual(target.read_text(), "manual unknown edit\n")

    def test_unknown_manifest_edit_after_replace_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _transaction, _old_target, _old_manifest = self.shadow(Path(tmp))
            plan = plan_adoption(project, "publication")
            with self.assertRaises(InjectedTransactionFailure):
                execute_adoption(plan, fail_at="after:targets_replaced")
            manifest = project / ".pops/manifest.toml"
            manifest.write_text(manifest.read_text() + "\n[manual]\nvalue = \"unknown\"\n")
            findings = recover_incomplete_transactions(project)
            self.assertIn("recovery.conflict", [item.code for item in findings])
            self.assertIn("[manual]", manifest.read_text())

    def shadow(self, parent: Path) -> tuple[Path, str, bytes, bytes | None]:
        project = copy_template(parent)
        publication_path = project / "_paperops/model/publication/publication-model.yml"
        publication = yaml.safe_load(publication_path.read_text())
        ledger = project / "_paperops/workflow/submission-ledger.yml"
        ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": publication}, sort_keys=False))
        code, raw, err = run_cli(["model", "diff", "publication", str(project), "--json"])
        self.assertEqual(code, 0, err)
        transaction = json.loads(raw)["transaction_id"]
        states = read_model_states(project)
        for name, state in tuple(states.items()):
            if name != "publication":
                states[name] = state.__class__(name, "v2-authoritative", "sha256:" + "a" * 64, state.last_shadow_transaction, "model-bootstrap-0001")
        write_model_states(project, states)
        return project, transaction, publication_path.read_bytes(), manifest_bytes(project)


if __name__ == "__main__":
    unittest.main()
