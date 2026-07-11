from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template, run_cli
from tests.test_paperops_model_check import valid_documents

from paperops.model_state import manifest_bytes, read_model_states, write_model_states
from paperops.model_migration.transaction import (
    InjectedTransactionFailure,
    execute_rollback,
    plan_rollback,
    recover_incomplete_transactions,
)


class ModelMigrationRollbackTest(unittest.TestCase):
    def test_latest_specific_dry_run_and_repeat_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, adoption, old_target = self.adopt_publication(Path(tmp))
            adopted_target = self.target(project).read_bytes()
            adopted_manifest = manifest_bytes(project)
            code, raw, err = run_cli(["model", "rollback", "publication", str(project), "--transaction", adoption, "--dry-run", "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual(self.target(project).read_bytes(), adopted_target)
            self.assertEqual(manifest_bytes(project), adopted_manifest)

            code, raw, err = run_cli(["model", "rollback", "publication", str(project), "--transaction", adoption, "--json"])
            self.assertEqual(code, 0, err)
            result = json.loads(raw)
            self.assertEqual(self.target(project).read_bytes(), old_target)
            self.assertEqual(read_model_states(project)["publication"].mode, "shadow-compare")
            self.assertTrue((project / ".paperops/snapshots" / result["transaction_id"] / "manifest.json").is_file())

            code, raw, _ = run_cli(["model", "rollback", "publication", str(project), "--json"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(raw)["reused"])

    def test_corrupt_or_missing_snapshot_blocks_without_mutation(self) -> None:
        for kind in ("corrupt", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                project, adoption, _old_target = self.adopt_publication(Path(tmp))
                adopted = self.target(project).read_bytes()
                snapshot = project / ".paperops/snapshots" / adoption
                if kind == "corrupt":
                    restored = snapshot / "_paperops/model/publication/publication-model.yml"
                    restored.write_text(restored.read_text() + "# corrupt\n")
                    expected = "transaction.snapshot_hash"
                else:
                    shutil.rmtree(snapshot)
                    expected = "transaction.snapshot_manifest"
                code, raw, _ = run_cli(["model", "rollback", "publication", str(project), "--json"])
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(raw)["findings"][0]["code"], expected)
                self.assertEqual(self.target(project).read_bytes(), adopted)

    def test_manual_target_edit_blocks_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _adoption, _old_target = self.adopt_publication(Path(tmp))
            self.target(project).write_text("manual edit\n")
            code, raw, _ = run_cli(["model", "rollback", "publication", str(project), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "transaction.target_changed")
            self.assertEqual(self.target(project).read_text(), "manual edit\n")

    def test_interrupted_rollback_recovers_the_pre_rollback_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _adoption, _old_target = self.adopt_publication(Path(tmp))
            adopted_target = self.target(project).read_bytes()
            adopted_manifest = manifest_bytes(project)
            plan = plan_rollback(project, "publication")
            with self.assertRaises(InjectedTransactionFailure):
                execute_rollback(plan, fail_at="after:targets_replaced")
            findings = recover_incomplete_transactions(project)
            self.assertNotIn("recovery.conflict", [item.code for item in findings])
            self.assertEqual(self.target(project).read_bytes(), adopted_target)
            self.assertEqual(manifest_bytes(project), adopted_manifest)

    def test_dependent_blocks_without_cascade_and_cascade_uses_reverse_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.adopt_editorial(Path(tmp))
            states = read_model_states(project)
            for name in ("manuscript", "issue"):
                states[name] = states[name].__class__(name, "v2-authoritative", "sha256:" + "b" * 64, "", "model-bootstrap-0001")
            write_model_states(project, states)
            self.diff_and_adopt_publication(project)
            states = read_model_states(project)
            for name in ("research", "manuscript", "issue"):
                states[name] = states[name].__class__(name)
            write_model_states(project, states)

            code, raw, _ = run_cli(["model", "rollback", "editorial", str(project), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "transaction.dependent")

            code, raw, err = run_cli(["model", "rollback", "editorial", str(project), "--cascade", "--json"])
            self.assertEqual(code, 0, err)
            rollback = json.loads(raw)["transaction_id"]
            journal = json.loads((project / ".paperops/migrations" / rollback / "journal.json").read_text())
            self.assertEqual(journal["models"], ["publication", "editorial", "results_hierarchy"])
            states = read_model_states(project)
            self.assertEqual(states["publication"].mode, "shadow-compare")
            self.assertEqual(states["editorial"].mode, "shadow-compare")
            self.assertEqual(states["results_hierarchy"].mode, "shadow-compare")

    def adopt_publication(self, parent: Path) -> tuple[Path, str, bytes]:
        project = copy_template(parent)
        old_target = self.target(project).read_bytes()
        states = read_model_states(project)
        for name in states:
            if name != "publication":
                states[name] = states[name].__class__(name, "v2-authoritative", "sha256:" + "a" * 64, "", "model-bootstrap-0001")
        write_model_states(project, states)
        adoption = self.diff_and_adopt_publication(project)
        return project, adoption, old_target

    def diff_and_adopt_publication(self, project: Path) -> str:
        publication = yaml.safe_load(self.target(project).read_text())
        ledger = project / "_paperops/workflow/submission-ledger.yml"
        ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": publication}, sort_keys=False))
        code, _raw, err = run_cli(["model", "diff", "publication", str(project), "--refresh", "--json"])
        self.assertEqual(code, 0, err)
        code, raw, err = run_cli(["model", "adopt", "publication", str(project), "--yes", "--json"])
        self.assertEqual(code, 0, err)
        return json.loads(raw)["transaction_id"]

    def adopt_editorial(self, parent: Path) -> Path:
        project = copy_template(parent)
        editorial, results = valid_documents()
        storyline = project / "_paperops/notes/views/storyline.md"
        storyline.write_text(
            "---\n"
            f"migration_editorial: {json.dumps(editorial)}\n"
            f"migration_results_hierarchy: {json.dumps(results)}\n"
            "---\n"
        )
        states = read_model_states(project)
        states["research"] = states["research"].__class__("research", "v2-authoritative", "sha256:" + "a" * 64, "", "model-bootstrap-0001")
        write_model_states(project, states)
        code, _raw, err = run_cli(["model", "diff", "editorial", str(project), "--json"])
        self.assertEqual(code, 0, err)
        code, _raw, err = run_cli(["model", "adopt", "editorial", str(project), "--yes", "--json"])
        self.assertEqual(code, 0, err)
        return project

    @staticmethod
    def target(project: Path) -> Path:
        return project / "_paperops/model/publication/publication-model.yml"


if __name__ == "__main__":
    unittest.main()
