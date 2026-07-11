from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template
from tests.test_manuscript_model import block, section

from paperops.model_migration.adapters.manuscript import ManuscriptAdapter
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.types import MigrationInput


class ManuscriptMigrationAdapterTest(unittest.TestCase):
    def test_structural_manifest_emits_ordered_records_without_tex_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            section_document = section()
            block_document = block()
            section_document["research_refs"] = []
            section_document["editorial_move_refs"] = []
            for key in ("claim_refs", "result_refs", "source_refs", "figure_refs"):
                block_document[key] = []
            block_document["compiled_from"]["input_ids"] = []
            block_document["compiled_from"]["input_hashes"] = []
            self.write_manifest(project, [section_document], [block_document])
            ja = project / "manuscript/ja/sections/20_results.tex"
            en = project / "manuscript/en/sections/20_results.tex"
            ja.write_text("% block: results:block-1:ja\n秘密の本文です。\n")
            en.write_text("% block: results:block-1:en\nPrivate prose.\n")
            before = (ja.read_bytes(), en.read_bytes())
            candidate = ManuscriptAdapter().materialize(MigrationInput(project, "manuscript", ()))
            self.assertEqual([item.code for item in candidate.findings], [])
            self.assertEqual(validate_conservation(candidate.inventory, candidate), ())
            payload = b"".join(item.content for item in candidate.documents)
            self.assertNotIn("秘密の本文".encode(), payload)
            self.assertNotIn(b"Private prose", payload)
            self.assertEqual(before, (ja.read_bytes(), en.read_bytes()))

    def test_missing_lineage_marker_and_research_approval_are_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            self.write_manifest(project, [section()], [block()])
            candidate = ManuscriptAdapter().materialize(MigrationInput(project, "manuscript", ()))
            codes = [item.code for item in candidate.findings]
            self.assertIn("migration.unresolved", codes)
            self.assertIn("approval.missing", codes)

    def test_all_section_kinds_positions_and_manual_tex_changes_affect_only_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            sections = []
            blocks = []
            for position, kind in enumerate(
                ("abstract", "introduction", "methods", "results", "discussion", "conclusion", "supplement"),
                1,
            ):
                section_document = section()
                section_document.update({"id": f"SEC-{position:04d}", "section_kind": kind, "ordered_block_ids": [f"BLK-{position:04d}"], "research_refs": [], "editorial_move_refs": []})
                block_document = block()
                block_document.update({"id": f"BLK-{position:04d}", "section_id": f"SEC-{position:04d}", "position": 1, "ja_tex_block_id": f"{kind}:1:ja", "en_tex_block_id": f"{kind}:1:en"})
                for key in ("claim_refs", "result_refs", "source_refs", "figure_refs"):
                    block_document[key] = []
                block_document["compiled_from"]["input_ids"] = []
                block_document["compiled_from"]["input_hashes"] = []
                sections.append(section_document)
                blocks.append(block_document)
            self.write_manifest(project, sections, blocks, marker_check=False)
            adapter = ManuscriptAdapter()
            first = adapter.materialize(MigrationInput(project, "manuscript", ()))
            self.assertEqual([item.code for item in first.findings], [])
            manifest = project / "_paperops/contracts/manuscript-migration.yml"
            manifest.write_text(manifest.read_text() + "# manual note\n")
            changed = adapter.materialize(MigrationInput(project, "manuscript", ()))
            self.assertEqual(
                [item.semantic_hash for item in first.documents],
                [item.semantic_hash for item in changed.documents],
            )
            self.assertNotEqual(first.inventory[0].source_hash, changed.inventory[0].source_hash)

    @staticmethod
    def write_manifest(project: Path, sections: list[dict], blocks: list[dict], *, marker_check: bool = True) -> None:
        path = project / "_paperops/contracts/manuscript-migration.yml"
        path.write_text(yaml.safe_dump({"schema_version": 1, "marker_check": marker_check, "sections": sections, "blocks": blocks}, sort_keys=False))


if __name__ == "__main__":
    unittest.main()
