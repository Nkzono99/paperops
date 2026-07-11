from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template
from tests.test_paperops_model_check import valid_documents

from paperops.model_migration.adapters.editorial import EditorialAdapter
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.types import MigrationInput
from paperops.model_validation import run_model_validation


class EditorialMigrationAdapterTest(unittest.TestCase):
    def test_valid_typed_pair_is_reused_and_strict_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            self.write_pair(project, editorial, results)
            (project / "_paperops/notes/views/storyline.md").unlink()
            candidate = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertEqual(candidate.findings, ())
            self.assertEqual(len(candidate.documents), 2)
            self.assertEqual(validate_conservation(candidate.inventory, candidate), ())
            first_hashes = [item.semantic_hash for item in candidate.documents]
            repeated = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertEqual(first_hashes, [item.semantic_hash for item in repeated.documents])
            self.write_candidate(project, candidate)
            self.assertTrue(run_model_validation(project, "editorial", strict=True).ok)

    def test_missing_typed_pair_can_use_only_explicit_structured_storyline_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            for name in ("editorial-model.yml", "results-hierarchy.yml"):
                (project / "_paperops/model/editorial" / name).unlink()
            storyline = project / "_paperops/notes/views/storyline.md"
            storyline.write_text(
                "---\n"
                f"migration_editorial: {json.dumps(editorial, ensure_ascii=False)}\n"
                f"migration_results_hierarchy: {json.dumps(results, ensure_ascii=False)}\n"
                "---\n# Storyline\n"
            )
            candidate = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertEqual([item.code for item in candidate.findings], [])
            self.write_candidate(project, candidate)
            self.assertTrue(run_model_validation(project, "editorial", strict=True).ok)

    def test_present_malformed_typed_results_never_falls_back_to_storyline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            self.write_pair(project, editorial, results)
            results["unknown"] = True
            (project / "_paperops/model/editorial/results-hierarchy.yml").write_text(
                yaml.safe_dump(results, sort_keys=False)
            )
            storyline = project / "_paperops/notes/views/storyline.md"
            storyline.write_text(
                "---\n"
                f"migration_results_hierarchy: {json.dumps(valid_documents()[1])}\n"
                "---\n"
            )
            candidate = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertEqual(candidate.documents, ())
            self.assertIn("schema.additional", [item.code for item in candidate.findings])

    def test_result_order_mismatch_is_blocking_and_hash_changes_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            editorial["results_hierarchy"]["item_ids"] = []
            self.write_pair(project, editorial, results)
            (project / "_paperops/notes/views/storyline.md").unlink()
            candidate = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertIn("migration.unresolved", [item.code for item in candidate.findings])
            before = candidate.documents[0].semantic_hash
            editorial["reader_transformation"]["reader_after"] = "A revised transformation."
            self.write_pair(project, editorial, results)
            changed = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertNotEqual(before, changed.documents[0].semantic_hash)

    def test_legacy_storyline_without_explicit_mapping_blocks_typed_editorial_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            editorial, results = valid_documents()
            self.write_pair(project, editorial, results)
            candidate = EditorialAdapter().materialize(MigrationInput(project, "editorial", ()))
            self.assertEqual(candidate.documents, ())
            self.assertIn("migration.unresolved", [item.code for item in candidate.findings])

    @staticmethod
    def write_pair(project: Path, editorial: dict, results: dict) -> None:
        directory = project / "_paperops/model/editorial"
        (directory / "editorial-model.yml").write_text(yaml.safe_dump(editorial, sort_keys=False))
        (directory / "results-hierarchy.yml").write_text(yaml.safe_dump(results, sort_keys=False))

    @staticmethod
    def write_candidate(project: Path, candidate) -> None:
        for document in candidate.documents:
            (project / document.relative_path).write_bytes(document.content)


if __name__ == "__main__":
    unittest.main()
