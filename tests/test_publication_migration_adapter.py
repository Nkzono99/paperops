from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template
from tests.test_publication_model import publication

from paperops.model_migration.adapters.publication import PublicationAdapter
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.types import MigrationInput
from paperops.model_validation import run_model_validation


class PublicationMigrationAdapterTest(unittest.TestCase):
    def test_ledger_preserves_candidate_round_axes_without_copying_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            document = publication()
            self.write_ledger(project, document)
            artifact = project / "submission/example/round-1/manuscript.pdf"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"submitted immutable bytes")
            before = artifact.read_bytes()
            candidate = PublicationAdapter().materialize(MigrationInput(project, "publication", ()))
            self.assertEqual(candidate.findings, ())
            self.assertEqual(validate_conservation(candidate.inventory, candidate), ())
            self.assertEqual(before, artifact.read_bytes())
            self.assertNotIn(before, candidate.documents[0].content)
            emitted = yaml.safe_load(candidate.documents[0].content)
            self.assertEqual(emitted["authoring"]["state"], "reconciled")
            self.assertEqual(emitted["current_candidate"]["status"], "gated")
            self.assertTrue(emitted["rounds"][0]["immutable"])
            (project / candidate.documents[0].relative_path).write_bytes(candidate.documents[0].content)
            self.assertTrue(run_model_validation(project, "publication", phase="schema", strict=True).ok)

    def test_submitted_round_requires_immutable_snapshot_and_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            document = publication()
            document["rounds"][0]["immutable"] = False
            document["rounds"][0]["source_commit"] = ""
            document["rounds"][0]["snapshot_manifest_ref"] = ""
            self.write_ledger(project, document)
            candidate = PublicationAdapter().materialize(MigrationInput(project, "publication", ()))
            self.assertIn("immutability.submitted_round", [item.code for item in candidate.findings])
            self.assertIn("migration.unresolved", [item.code for item in candidate.findings])

    def test_unresolved_prediction_blocks_publication_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            self.write_ledger(project, publication())
            analysis = project / "_paperops/model/issues/analysis/AREQ-0001.yml"
            analysis.parent.mkdir(parents=True, exist_ok=True)
            analysis.write_text("record_type: analysis_request\nid: AREQ-0001\nstatus: predicted\n")
            candidate = PublicationAdapter().materialize(MigrationInput(project, "publication", ()))
            self.assertIn("migration.unresolved", [item.code for item in candidate.findings])

    @staticmethod
    def write_ledger(project: Path, document: dict) -> None:
        ledger = project / "_paperops/workflow/submission-ledger.yml"
        ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": document}, sort_keys=False))


if __name__ == "__main__":
    unittest.main()
