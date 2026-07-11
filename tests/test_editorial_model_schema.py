from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "template" / "scripts"))

from paperops_schema import (  # noqa: E402
    SchemaDefinitionError,
    load_document,
    load_registry,
    validate_schema,
)


TEMPLATE = ROOT / "template"
SCHEMA_DIR = TEMPLATE / "_paperops" / "defaults" / "schemas"


class EditorialModelSchemaTest(unittest.TestCase):
    def test_registry_resolves_managed_schema_and_project_default(self) -> None:
        registry = load_registry(TEMPLATE)

        self.assertEqual(registry.version, 1)
        self.assertEqual(registry.validator_profile, "paperops-schema-v1")
        self.assertEqual(set(registry.entries), {"editorial", "results_hierarchy"})

        editorial = registry.entries["editorial"]
        self.assertEqual(editorial.name, "editorial")
        self.assertEqual(
            editorial.schema_path,
            SCHEMA_DIR / "editorial-model.schema.json",
        )
        self.assertEqual(
            editorial.default_path,
            TEMPLATE / "_paperops" / "model" / "editorial" / "editorial-model.yml",
        )
        self.assertEqual(editorial.schema_version, 1)
        self.assertEqual(editorial.authority, "project-owned")
        self.assertEqual(editorial.hash_profile, "semantic-v1")
        self.assertEqual(editorial.hash_excluded_paths, ("/metadata/updated_at",))
        self.assertEqual(
            registry.entries["results_hierarchy"].hash_excluded_paths,
            (),
        )

    def test_registry_rejects_unknown_version_and_profile(self) -> None:
        cases = [
            ("registry_version", 2, "registry.version"),
            ("validator_profile", "unknown", "registry.profile"),
        ]
        for key, value, code in cases:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._copy_registry_tree(root)
                registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
                registry = load_document(registry_path)
                registry[key] = value
                registry_path.write_text(json.dumps(registry), encoding="utf-8")

                with self.assertRaisesRegex(SchemaDefinitionError, code):
                    load_registry(root)

    def test_registry_rejects_missing_schema_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_registry_tree(root)
            (root / "_paperops" / "defaults" / "schemas" / "editorial-model.schema.json").unlink()

            with self.assertRaisesRegex(SchemaDefinitionError, "registry.schema_missing"):
                load_registry(root)

    def test_registry_rejects_absolute_and_traversing_paths(self) -> None:
        cases = [
            ("schema", "/tmp/editorial.schema.json"),
            ("schema", "../editorial.schema.json"),
            ("default_path", "/tmp/editorial.yml"),
            ("default_path", "../editorial.yml"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._copy_registry_tree(root)
                registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
                registry = load_document(registry_path)
                registry["models"]["editorial"][key] = value
                registry_path.write_text(json.dumps(registry), encoding="utf-8")

                with self.assertRaisesRegex(SchemaDefinitionError, "registry.path"):
                    load_registry(root)

    def test_editorial_starter_passes_schema_validation(self) -> None:
        registry = load_registry(TEMPLATE)
        editorial = registry.entries["editorial"]

        document = load_document(editorial.default_path)
        schema = load_document(editorial.schema_path)

        self.assertEqual(validate_schema(document, schema), [])

    @staticmethod
    def _copy_registry_tree(root: Path) -> None:
        destination = root / "_paperops" / "defaults" / "schemas"
        destination.parent.mkdir(parents=True)
        shutil.copytree(SCHEMA_DIR, destination)


if __name__ == "__main__":
    unittest.main()
