from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.legacy import inventory_tree, load_legacy_card
from paperops.model_migration.types import (
    CandidateDocument,
    InventoryItem,
    MigrationCandidate,
)


class ModelMigrationCatalogTest(unittest.TestCase):
    def test_reader_preserves_explicit_frontmatter_definitions_and_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "card.md"
            path.write_text(
                "---\n"
                "id: CLM-0001\n"
                "status: draft\n"
                "links: [RES-0001, FIG-0001]\n"
                "target:\n"
                "  kind: claim\n"
                "  id: CLM-0001\n"
                "routes:\n"
                "  - evidence\n"
                "  - manuscript\n"
                "---\n\n"
                "# Claim\n\n"
                "## Scope\n\n"
                "- scope: bounded claim\n"
                "- limitation: one regime\n\n"
                "| quantity_id | unit |\n"
                "| --- | --- |\n"
                "| QTY-0001 | run |\n",
                encoding="utf-8",
            )
            card = load_legacy_card(path, project_root=Path(tmp))
        self.assertEqual(card.source_path, "card.md")
        self.assertEqual(card.frontmatter["id"].value, "CLM-0001")
        self.assertEqual(card.frontmatter["links"].value, ("RES-0001", "FIG-0001"))
        self.assertEqual(card.frontmatter["target.kind"].value, "claim")
        self.assertEqual(card.frontmatter["target.id"].value, "CLM-0001")
        self.assertEqual(card.frontmatter["routes"].value, ("evidence", "manuscript"))
        scope = next(section for section in card.sections if section.title == "Scope")
        self.assertEqual(scope.definitions["scope"].value, "bounded claim")
        self.assertEqual(scope.tables[0].rows[0]["quantity_id"], "QTY-0001")
        self.assertEqual(card.findings, ())

    def test_reader_reports_duplicate_keys_unknown_material_and_private_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "card.md"
            path.write_text(
                "---\n"
                "id: CLM-0001\n"
                "id: CLM-0002\n"
                "raw_path: /private/run/output.h5\n"
                "remote: https://alice:secret@example.test/data\n"
                "---\n\n"
                "## Scope\n\n"
                "This prose cannot be mapped mechanically.\n",
                encoding="utf-8",
            )
            card = load_legacy_card(path, project_root=Path(tmp))
        codes = [finding.code for finding in card.findings]
        self.assertIn("migration.duplicate", codes)
        self.assertIn("migration.unknown_field", codes)
        self.assertEqual(codes.count("migration.confidential"), 2)
        self.assertTrue(all("secret" not in finding.message for finding in card.findings))

    def test_inventory_is_hash_stable_and_reports_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cards = root / "cards"
            cards.mkdir()
            one = cards / "one.md"
            two = cards / "two.md"
            one.write_text("---\nid: CLM-0001\n---\n", encoding="utf-8")
            two.write_text("---\nid: CLM-0001\n---\n", encoding="utf-8")
            first = inventory_tree(root, (Path("cards"),))
            second = inventory_tree(root, (Path("cards"),))
            self.assertEqual(first.cards[0].source_hash, second.cards[0].source_hash)
            self.assertIn("migration.duplicate", [item.code for item in first.findings])
            one.write_text("---\nid: CLM-0002\n---\n", encoding="utf-8")
            changed = inventory_tree(root, (Path("cards"),))
            self.assertNotEqual(first.cards[0].source_hash, changed.cards[0].source_hash)

    def test_inventory_reports_missing_escape_and_symlink_without_reading_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            outside = Path(outside_tmp)
            (outside / "secret.md").write_text("---\nid: CLM-secret\n---\n")
            (root / "linked").symlink_to(outside, target_is_directory=True)
            for allowed, code in (
                ((Path("missing"),), "migration.missing"),
                ((Path("../escape"),), "migration.path"),
                ((Path("linked"),), "migration.path"),
            ):
                with self.subTest(allowed=allowed):
                    result = inventory_tree(root, allowed)
                    self.assertEqual(result.cards, ())
                    self.assertEqual(result.findings[0].code, code)

    def test_inventory_rejects_special_file_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            special = root / "fifo"
            import os

            os.mkfifo(special)
            result = inventory_tree(root, (Path("fifo"),))
            self.assertEqual(result.cards, ())
            self.assertEqual(result.findings[0].code, "migration.path")

    def test_conservation_accepts_complete_explicit_dispositions(self) -> None:
        items = (
            self.item("claim.scope", "mapped", target_id="CLM-0001"),
            self.item(
                "figure.obligation",
                "deferred",
                legacy_id="VO-0001",
                reason="P3 compiler input",
                followup_phase="P3",
            ),
            self.item(
                "confidential.raw_reviewer_text",
                "local-only",
                legacy_id="REV-0001",
                reason="confidential source remains local",
            ),
        )
        candidate = MigrationCandidate(
            model_name="research",
            documents=(CandidateDocument("claim.yml", "CLM-0001", "sha256:" + "2" * 64),),
            inventory=items,
            findings=(),
        )
        self.assertEqual(validate_conservation(items, candidate), ())

    def test_conservation_blocks_missing_or_invalid_dispositions(self) -> None:
        cases = (
            (self.item("claim.scope", "mapped", target_id="CLM-missing"), "migration.unmapped"),
            (self.item("claim.scope", "unsupported"), "migration.unsupported"),
            (self.item("claim.scope", "deferred", reason="later"), "migration.disposition"),
            (self.item("claim.scope", "local-only", reason="private"), "migration.disposition"),
            (self.item("claim.scope", "invented"), "migration.disposition"),
        )
        for item, expected in cases:
            with self.subTest(item=item):
                candidate = MigrationCandidate("research", (), (item,), ())
                codes = [finding.code for finding in validate_conservation((item,), candidate)]
                self.assertIn(expected, codes)

    def test_conservation_detects_duplicate_disposition_and_source_drift(self) -> None:
        old = self.item("claim.scope", "mapped", target_id="CLM-0001")
        current = replace(old, source_hash="sha256:" + "9" * 64)
        candidate = MigrationCandidate(
            "research",
            (CandidateDocument("claim.yml", "CLM-0001", "sha256:" + "2" * 64),),
            (old, old),
            (),
        )
        codes = [finding.code for finding in validate_conservation((current,), candidate)]
        self.assertIn("migration.disposition", codes)
        self.assertIn("migration.source_changed", codes)

    @staticmethod
    def item(
        family: str,
        disposition: str,
        *,
        legacy_id: str = "CLM-0001",
        target_id: str = "",
        reason: str = "",
        followup_phase: str = "",
    ) -> InventoryItem:
        return InventoryItem(
            family=family,
            legacy_id=legacy_id,
            source_path="_paperops/claims/claims/CLM-0001.md",
            pointer="/scope",
            source_hash="sha256:" + "1" * 64,
            disposition=disposition,
            target_id=target_id,
            reason=reason,
            followup_phase=followup_phase,
        )


if __name__ == "__main__":
    unittest.main()
