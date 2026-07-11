from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "template" / "scripts"))

from paperops_schema import (  # noqa: E402
    SchemaDefinitionError,
    load_document,
    load_registry,
    validate_document_version,
    validate_schema,
)


TEMPLATE = ROOT / "template"
SCHEMA_DIR = TEMPLATE / "_paperops" / "defaults" / "schemas"


class EditorialModelSchemaTest(unittest.TestCase):
    def test_registry_resolves_managed_schema_and_project_default(self) -> None:
        registry = load_registry(TEMPLATE)

        self.assertEqual(registry.version, 1)
        self.assertEqual(registry.validator_profile, "paperops-schema-v1")
        self.assertEqual(
            set(registry.entries),
            {"editorial", "results_hierarchy", "research", "manuscript"},
        )

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
        self.assertEqual(editorial.document_kind, "aggregate")
        self.assertEqual(editorial.record_sets, {})
        self.assertIsNone(editorial.dependency_profile)
        self.assertEqual(
            registry.entries["results_hierarchy"].hash_excluded_paths,
            (),
        )

    def test_results_registry_entry_is_fully_resolved(self) -> None:
        entry = load_registry(TEMPLATE).entries["results_hierarchy"]

        self.assertEqual(entry.name, "results_hierarchy")
        self.assertEqual(entry.schema_path, SCHEMA_DIR / "results-hierarchy.schema.json")
        self.assertEqual(entry.schema_version, 1)
        self.assertEqual(entry.authority, "project-owned")
        self.assertEqual(
            entry.default_path,
            TEMPLATE / "_paperops" / "model" / "editorial" / "results-hierarchy.yml",
        )
        self.assertEqual(entry.hash_profile, "semantic-v1")
        self.assertEqual(entry.hash_excluded_paths, ())

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

    def test_registry_requires_p1a_core_models_and_rejects_unknown_models(self) -> None:
        cases = [
            ("editorial", None, "registry.model_missing"),
            ("results_hierarchy", None, "registry.model_missing"),
            ("unknown", {"schema": "unknown.json"}, "registry.model_unknown"),
        ]
        for name, value, code in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._copy_registry_tree(root)
                registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
                registry = load_document(registry_path)
                if value is None:
                    del registry["models"][name]
                else:
                    registry["models"][name] = value
                registry_path.write_text(json.dumps(registry), encoding="utf-8")

                with self.assertRaisesRegex(SchemaDefinitionError, code):
                    load_registry(root)

    def test_registry_rejects_unsupported_model_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_registry_tree(root)
            registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
            registry = load_document(registry_path)
            registry["models"]["editorial"]["schema_version"] = 2
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaisesRegex(SchemaDefinitionError, "registry.model_version"):
                load_registry(root)

    def test_document_version_contract_rejects_registry_mismatch(self) -> None:
        entry = load_registry(TEMPLATE).entries["editorial"]

        validate_document_version(entry, {"schema_version": 1})
        with self.assertRaisesRegex(SchemaDefinitionError, "registry.document_version"):
            validate_document_version(entry, {"schema_version": 2})

    def test_registry_normalizes_document_load_failures(self) -> None:
        cases = [
            (b"models: [\n", "malformed YAML"),
            (b"\xff\xfe", "invalid UTF-8"),
            (b"models:\n  editorial: 1\n  editorial: 2\n", "duplicate key"),
        ]
        for payload, label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
                registry_path.parent.mkdir(parents=True)
                registry_path.write_bytes(payload)

                with self.assertRaisesRegex(SchemaDefinitionError, "registry.invalid"):
                    load_registry(root)

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SchemaDefinitionError, "registry.invalid"):
                load_registry(Path(tmp))

        original = SchemaDefinitionError("schema.original: keep this definition error")
        with mock.patch("paperops_schema.load_document", side_effect=original):
            with self.assertRaises(SchemaDefinitionError) as raised:
                load_registry(TEMPLATE)
        self.assertIs(raised.exception, original)

    def test_registry_rejects_invalid_or_duplicate_hash_pointers(self) -> None:
        cases = [
            (["/metadata/~2bad"], "registry.hash_pointer"),
            (["/metadata/~"], "registry.hash_pointer"),
            (["/metadata/updated_at", "/metadata/updated_at"], "registry.hash_duplicate"),
        ]
        for pointers, code in cases:
            with self.subTest(pointers=pointers), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._copy_registry_tree(root)
                registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
                registry = load_document(registry_path)
                registry["models"]["editorial"]["hash_excluded_paths"] = pointers
                registry_path.write_text(json.dumps(registry), encoding="utf-8")

                with self.assertRaisesRegex(SchemaDefinitionError, code):
                    load_registry(root)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_registry_tree(root)
            registry_path = root / "_paperops" / "defaults" / "schemas" / "registry.yml"
            registry = load_document(registry_path)
            registry["models"]["editorial"]["hash_excluded_paths"] = [
                "/extensions/x-owner-a~0b~1c"
            ]
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            self.assertEqual(
                load_registry(root).entries["editorial"].hash_excluded_paths,
                ("/extensions/x-owner-a~0b~1c",),
            )

    def test_editorial_starter_passes_schema_validation(self) -> None:
        registry = load_registry(TEMPLATE)
        editorial = registry.entries["editorial"]

        document = load_document(editorial.default_path)
        schema = load_document(editorial.schema_path)

        self.assertEqual(validate_schema(document, schema), [])

    def test_editorial_schema_requires_every_top_level_field(self) -> None:
        document, schema = self._editorial_document_and_schema()
        for field in list(document):
            with self.subTest(field=field):
                invalid = dict(document)
                del invalid[field]
                findings = validate_schema(invalid, schema)
                self.assertIn("schema.required", {finding.code for finding in findings})

    def test_editorial_schema_rejects_top_level_and_nested_unknown_fields(self) -> None:
        document, schema = self._editorial_document_and_schema()
        cases = [
            (document, "unknown", "/unknown"),
            (document["reader_transformation"], "unknown", "/reader_transformation/unknown"),
            (document["claim_roles"]["foreground"], "unknown", "/claim_roles/foreground/unknown"),
        ]
        for target, field, pointer in cases:
            with self.subTest(pointer=pointer):
                target[field] = True
                findings = validate_schema(document, schema)
                self.assertIn(
                    ("schema.additional", pointer),
                    {(finding.code, finding.pointer) for finding in findings},
                )
                del target[field]

    def test_editorial_schema_enforces_all_id_patterns(self) -> None:
        document, schema = self._editorial_document_and_schema()
        cases = [
            (document, "model_id", "/model_id"),
            (document["story_candidates"][0], "id", "/story_candidates/0/id"),
            (document["argument_moves"][0], "id", "/argument_moves/0/id"),
            (document["visual_obligations"][0], "id", "/visual_obligations/0/id"),
            (document["claim_roles"]["foreground"]["claim_ids"], 0, "/claim_roles/foreground/claim_ids/0"),
            (document["visual_obligations"][0]["figure_ids"], 0, "/visual_obligations/0/figure_ids/0"),
            (document["results_hierarchy"]["item_ids"], 0, "/results_hierarchy/item_ids/0"),
        ]
        for target, key, pointer in cases:
            with self.subTest(pointer=pointer):
                original = target[key]
                target[key] = "BAD-0001"
                findings = validate_schema(document, schema)
                self.assertIn(
                    ("schema.pattern", pointer),
                    {(finding.code, finding.pointer) for finding in findings},
                )
                target[key] = original

    def test_editorial_schema_requires_all_four_claim_roles(self) -> None:
        document, schema = self._editorial_document_and_schema()
        for role in ["foreground", "supporting", "supplement", "cut"]:
            with self.subTest(role=role):
                value = document["claim_roles"].pop(role)
                findings = validate_schema(document, schema)
                self.assertIn(
                    ("schema.required", f"/claim_roles/{role}"),
                    {(finding.code, finding.pointer) for finding in findings},
                )
                document["claim_roles"][role] = value

    def test_results_schema_preserves_id_required_and_additional_semantics(self) -> None:
        entry = load_registry(TEMPLATE).entries["results_hierarchy"]
        schema = load_document(entry.schema_path)
        document = load_document(entry.default_path)
        self.assertEqual(validate_schema(document, schema), [])

        invalid_id = json.loads(json.dumps(document))
        invalid_id["items"][0]["id"] = "BAD-0001"
        self.assertIn("schema.pattern", {f.code for f in validate_schema(invalid_id, schema)})

        additional = json.loads(json.dumps(document))
        additional["items"][0]["unknown"] = True
        self.assertIn("schema.additional", {f.code for f in validate_schema(additional, schema)})

        missing = json.loads(json.dumps(document))
        del missing["items"][0]["answer"]
        self.assertIn("schema.required", {f.code for f in validate_schema(missing, schema)})

    @staticmethod
    def _editorial_document_and_schema() -> tuple[dict[str, object], dict[str, object]]:
        registry = load_registry(TEMPLATE)
        schema = load_document(registry.entries["editorial"].schema_path)
        document = load_document(registry.entries["editorial"].default_path)
        document["story_candidates"] = [
            {
                "id": "STY-0001",
                "label": "story",
                "thesis": "thesis",
                "result_order": ["RHI-0001"],
                "argument_move_ids": ["MOV-0001"],
                "status": "selected",
                "selection_reason": "reason",
                "rejection_reason": "",
            }
        ]
        document["selected_story_id"] = "STY-0001"
        document["claim_roles"]["foreground"] = {
            "claim_ids": ["CLM-0001"],
            "none_reason": "",
        }
        document["argument_moves"] = [
            {
                "id": "MOV-0001",
                "position": 1,
                "stance": "assert",
                "reader_question": "question",
                "assertion": "assertion",
                "claim_ids": ["CLM-0001"],
                "result_item_ids": ["RHI-0001"],
                "next_move_id": "",
            }
        ]
        document["visual_obligations"] = [
            {
                "id": "VIS-0001",
                "reader_task": "task",
                "takeaway": "takeaway",
                "claim_ids": ["CLM-0001"],
                "preferred_form": "plot",
                "status": "satisfied",
                "waiver_reason": "",
                "figure_ids": ["FIG-0001"],
            }
        ]
        document["results_hierarchy"]["item_ids"] = ["RHI-0001"]
        return document, schema

    @staticmethod
    def _copy_registry_tree(root: Path) -> None:
        destination = root / "_paperops" / "defaults" / "schemas"
        destination.parent.mkdir(parents=True)
        shutil.copytree(SCHEMA_DIR, destination)


if __name__ == "__main__":
    unittest.main()
