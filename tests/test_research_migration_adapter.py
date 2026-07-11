from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template

sys.path.insert(0, str(ROOT / "template/scripts"))
from tests.test_research_model import claim, figure, gate, result, source

from paperops.model_migration.adapters.research import ResearchAdapter
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.types import MigrationInput
from paperops.model_validation import run_model_validation


LEGACY_DIRECTORIES = {
    "claim": "_paperops/claims/claims",
    "result": "_paperops/evidence/results",
    "figure": "_paperops/evidence/figures",
    "source": "_paperops/evidence/sources",
    "scientific_gate": "_paperops/claims/gates",
}


class ResearchMigrationAdapterTest(unittest.TestCase):
    def test_complete_legacy_cards_materialize_to_strict_valid_research_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.project(Path(tmp))
            candidate = ResearchAdapter().materialize(
                MigrationInput(project, "research", ())
            )
            errors = [item for item in candidate.findings if item.severity == "error"]
            self.assertEqual(errors, [], errors)
            self.assertNotIn(
                "migration.unknown_field",
                [item.code for item in candidate.findings],
            )
            self.assertEqual(
                {document.object_id for document in candidate.documents},
                {"research", "CLM-0001", "RES-0001", "FIG-0001", "SRC-0001", "GATE-0001"},
            )
            self.assertEqual(validate_conservation(candidate.inventory, candidate), ())
            self.write_candidate(project, candidate)
            validation = run_model_validation(project, "research", strict=True)
            self.assertTrue(validation.ok, validation.findings)

    def test_materialization_is_stable_and_source_changes_change_candidate_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.project(Path(tmp))
            adapter = ResearchAdapter()
            first = adapter.materialize(MigrationInput(project, "research", ()))
            second = adapter.materialize(MigrationInput(project, "research", ()))
            self.assertEqual(
                [(item.object_id, item.semantic_hash, item.content) for item in first.documents],
                [(item.object_id, item.semantic_hash, item.content) for item in second.documents],
            )
            claim_path = project / "_paperops/claims/claims/CLM-0001.md"
            claim_path.write_text(
                claim_path.read_text().replace(
                    "The controlled comparison supports the bounded mechanism.",
                    "The controlled comparison supports a revised bounded mechanism.",
                )
            )
            changed = adapter.materialize(MigrationInput(project, "research", ()))
            before = {item.object_id: item.semantic_hash for item in first.documents}
            after = {item.object_id: item.semantic_hash for item in changed.documents}
            self.assertNotEqual(before["CLM-0001"], after["CLM-0001"])

    def test_unknown_private_duplicate_and_incomplete_pairing_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.project(Path(tmp))
            claim_path = project / "_paperops/claims/claims/CLM-0001.md"
            claim_path.write_text(
                claim_path.read_text().replace(
                    "updated: 2026-07-11",
                    "updated: 2026-07-11\nmystery: cannot-map\nraw_path: /private/run/output.h5",
                )
            )
            gate_path = project / "_paperops/claims/gates/GATE-0001.md"
            gate_path.unlink()
            duplicate = project / "_paperops/claims/claims/duplicate.md"
            duplicate.write_text(claim_path.read_text())
            candidate = ResearchAdapter().materialize(
                MigrationInput(project, "research", ())
            )
            codes = [finding.code for finding in candidate.findings]
            self.assertIn("migration.unknown_field", codes)
            self.assertIn("migration.confidential", codes)
            self.assertIn("migration.duplicate", codes)
            self.assertIn("migration.unresolved", codes)
            private = [
                item for item in candidate.inventory if item.family == "claim.raw_path"
            ]
            self.assertEqual(private[0].disposition, "local-only")

    def test_missing_revision_and_duplicate_quantity_ids_are_not_invented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            documents = self.documents()
            documents[0].pop("revision")
            quantity = copy.deepcopy(documents[1]["quantity_contracts"][0])
            documents[1]["quantity_contracts"].append(quantity)
            project = self.project(Path(tmp), documents)
            candidate = ResearchAdapter().materialize(
                MigrationInput(project, "research", ())
            )
            codes = [finding.code for finding in candidate.findings]
            self.assertIn("migration.unresolved", codes)
            self.assertIn("migration.duplicate", codes)
            claim_document = json.loads(
                next(item.content for item in candidate.documents if item.object_id == "CLM-0001")
            )
            self.assertNotIn("revision", claim_document)

    def test_explicit_approval_and_gate_history_are_copied_without_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            documents = self.documents()
            documents[0]["approvals"] = [
                {
                    "approval_id": "APR-0001",
                    "kind": "scientific_scope",
                    "decision": "approved",
                    "object_revision": 1,
                    "object_hash": "sha256:" + "a" * 64,
                    "actor": "human",
                    "note": "Explicit legacy attestation.",
                }
            ]
            documents[4]["history"] = [
                {
                    "event_id": "HIS-0001",
                    "decision": "draft",
                    "note": "Explicit legacy gate history.",
                }
            ]
            project = self.project(Path(tmp), documents)
            candidate = ResearchAdapter().materialize(
                MigrationInput(project, "research", ())
            )
            emitted = {
                item.object_id: json.loads(item.content)
                for item in candidate.documents
                if item.object_id != "research"
            }
            self.assertEqual(emitted["CLM-0001"]["approvals"], documents[0]["approvals"])
            self.assertEqual(emitted["GATE-0001"]["history"], documents[4]["history"])
            self.assertEqual(emitted["RES-0001"]["approvals"], [])

    def project(
        self,
        parent: Path,
        documents: list[dict[str, object]] | None = None,
    ) -> Path:
        project = copy_template(parent)
        for relative in set(LEGACY_DIRECTORIES.values()):
            path = project / relative
            shutil.rmtree(path)
            path.mkdir(parents=True)
        for document in documents or self.documents():
            record_type = str(document["record_type"])
            path = project / LEGACY_DIRECTORIES[record_type] / f"{document['id']}.md"
            path.write_text(self.render_card(document), encoding="utf-8")
        return project

    @staticmethod
    def documents() -> list[dict[str, object]]:
        claim_document = claim()
        claim_document.update(
            {
                "status": "proposed",
                "gate_status": "draft",
                "human_approval": "needed",
                "abstract_conclusion_allowed": False,
                "approvals": [],
                "visual_obligation_refs": [],
                "manuscript_block_refs": [],
            }
        )
        result_document = result()
        result_document["manuscript_block_refs"] = []
        figure_document = figure()
        figure_document["visual_obligation_refs"] = []
        figure_document["manuscript_block_refs"] = []
        source_document = source()
        source_document["manuscript_block_refs"] = []
        gate_document = gate()
        gate_document.update(
            {
                "status": "draft",
                "gate_decision": "draft",
                "approved_writing_scope": "",
                "human_approval": "needed",
                "approvals": [],
                "history": [],
                "external_validation_gates": [],
            }
        )
        gate_document["central_assumptions"][0]["manuscript_block_refs"] = []
        return [
            claim_document,
            result_document,
            figure_document,
            source_document,
            gate_document,
        ]

    @staticmethod
    def render_card(document: dict[str, object]) -> str:
        value = copy.deepcopy(document)
        record_type = str(value.pop("record_type"))
        value.pop("schema_version", None)
        metadata = value.pop("metadata")
        statement = value.pop("statement", None)
        warrant = value.pop("warrant", None)
        observation = value.pop("observation", None)
        lines = ["---", f"type: {record_type}"]
        for key, item in value.items():
            lines.append(
                f"{key}: {json.dumps(item, ensure_ascii=False, separators=(',', ':'))}"
            )
        lines.append(f"updated: {metadata['updated_at']}")
        lines.extend(["---", ""])
        if statement is not None:
            lines.extend(["## 主張", "", str(statement), ""])
        if warrant is not None:
            lines.extend(["## Warrant", "", str(warrant), ""])
        if observation is not None:
            lines.extend(["## 観察", "", str(observation), ""])
        return "\n".join(lines)

    @staticmethod
    def write_candidate(project: Path, candidate) -> None:
        for document in candidate.documents:
            path = project / document.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(document.content)


if __name__ == "__main__":
    unittest.main()
