from __future__ import annotations

import unittest

from tests.helpers import ROOT

from paperops.cli.migrations import get_migration
from paperops.cli.scaffold import is_managed_update


SIX_MODELS = (
    "Research",
    "Editorial",
    "Results hierarchy",
    "Manuscript",
    "Issue",
    "Publication",
)


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class P1BDocumentationTest(unittest.TestCase):
    def test_managed_kernel_and_project_owned_state_have_opposite_update_boundaries(self) -> None:
        for relative in (
            "_paperops/defaults/schemas/registry.yml",
            "_paperops/defaults/schemas/publication-model.schema.json",
            "scripts/paperops_schema.py",
            "scripts/paperops_models.py",
            "scripts/check-paperops-models.py",
        ):
            with self.subTest(relative=relative):
                self.assertTrue(is_managed_update(relative))
        for relative in (
            "_paperops/model/editorial/editorial-model.yml",
            "_paperops/model/editorial/results-hierarchy.yml",
            "_paperops/model/research/index.yml",
            "_paperops/model/manuscript/index.yml",
            "_paperops/model/issues/index.yml",
            "_paperops/model/publication/publication-model.yml",
            "_paperops/model/research/claims/CLM-0001.yml",
        ):
            with self.subTest(relative=relative):
                self.assertFalse(is_managed_update(relative))

    def test_primary_docs_name_exact_six_model_scope_and_legacy_authority(self) -> None:
        for relative in (
            "README.md",
            "docs/architecture.md",
            "docs/current-specification.md",
            "template/README.md",
            "template/_paperops/model/README.md",
        ):
            document = text(relative)
            with self.subTest(relative=relative):
                for model_name in SIX_MODELS:
                    self.assertIn(model_name, document)
                self.assertIn("legacy", document.lower())
                self.assertIn("P2", document)

    def test_cli_and_downstream_interfaces_document_all_phases_and_hash_commands(self) -> None:
        cli = text("docs/cli.md")
        for phase in (
            "schema",
            "references",
            "semantics",
            "approvals",
            "dependencies",
            "hash",
        ):
            self.assertIn(f"`{phase}`", cli)
        self.assertIn("--print-dependency-hash", cli)
        self.assertIn("--object-id", cli)
        for relative in ("template/AGENTS.md", "template/CLAUDE.md"):
            document = text(relative)
            with self.subTest(relative=relative):
                self.assertIn("Publication", document)
                self.assertIn("approvals", document)
                self.assertIn("dependencies", document)
                self.assertIn("legacy", document.lower())

    def test_m0005_is_guide_only_and_preserves_project_state(self) -> None:
        migration = get_migration("M0-0005")
        self.assertIsNotNone(migration)
        assert migration is not None
        self.assertEqual(migration.moves, ())
        notes = " ".join(migration.notes).lower()
        self.assertIn("manual", notes)
        self.assertIn("never deletes", notes)
        guide = text("docs/migrations/v0.md")
        self.assertIn("M0-0005", guide)
        self.assertIn("guide-only", guide)
        for deferred in ("P2", "P3", "P4"):
            self.assertIn(deferred, guide)

    def test_disposition_inventory_keeps_every_legacy_field_family(self) -> None:
        inventory = text("docs/paperops2-disposition.md")
        required_families = (
            "claim card",
            "result card",
            "figure card",
            "source card",
            "scientific gate",
            "storyline",
            "section contract",
            "analysis request",
            "writing request",
            "feedback",
            "response",
            "review round",
            "submission ledger",
        )
        for family in required_families:
            with self.subTest(family=family):
                self.assertIn(family, inventory.lower())

    def test_changelog_and_skill_catalog_state_p1b_without_claiming_cutover(self) -> None:
        changelog = text("CHANGELOG.md")
        catalog = text("docs/skill-catalog.md")
        self.assertIn("PaperOps 2 P1-B", changelog)
        self.assertIn("dependency-v1", changelog)
        self.assertIn("Publication Model", changelog)
        for deferred in ("P2", "P3", "P4"):
            self.assertIn(deferred, catalog)
        self.assertIn("legacy", catalog.lower())


if __name__ == "__main__":
    unittest.main()
