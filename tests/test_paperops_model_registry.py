from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT


SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paperops_schema import (  # noqa: E402
    RecordSetEntry,
    SchemaDefinitionError,
    load_document,
    load_registry,
    validate_schema,
)


TEMPLATE = ROOT / "template"
SCHEMA_DIR = TEMPLATE / "_paperops" / "defaults" / "schemas"
MODEL_NAMES = {
    "research",
    "editorial",
    "results_hierarchy",
    "manuscript",
    "issue",
    "publication",
}


class PaperOpsModelRegistryTest(unittest.TestCase):
    def test_checked_in_registry_adds_index_models_without_changing_core_aggregates(self) -> None:
        registry = load_registry(TEMPLATE)

        self.assertEqual(
            set(registry.entries),
            {"editorial", "results_hierarchy", "research", "manuscript", "issue"},
        )
        for name in ("editorial", "results_hierarchy"):
            entry = registry.entries[name]
            with self.subTest(model=entry.name):
                self.assertEqual(entry.document_kind, "aggregate")
                self.assertEqual(entry.record_sets, {})
                self.assertIsNone(entry.dependency_profile)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = self.schema_dir(root)
            destination.parent.mkdir(parents=True)
            shutil.copytree(SCHEMA_DIR, destination)
            document = self.read_registry(root)
            document["models"].pop("research")
            document["models"].pop("manuscript")
            document["models"].pop("issue")
            for entry in document["models"].values():
                entry.pop("document_kind")
            self.write_registry(root, document)

            legacy_registry = load_registry(root)

        self.assertTrue(
            all(
                entry.document_kind == "aggregate"
                for entry in legacy_registry.entries.values()
            )
        )

    def test_registry_and_entry_unknown_keys_are_rejected(self) -> None:
        for target in ("registry", "entry"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = self.make_registry_root(Path(tmp))
                document = self.read_registry(root)
                if target == "registry":
                    document["validator_profiel"] = "typo"
                else:
                    document["models"]["editorial"]["hash_profiel"] = "typo"
                self.write_registry(root, document)

                with self.assertRaisesRegex(SchemaDefinitionError, "registry.invalid"):
                    load_registry(root)

    def test_complete_temporary_six_entry_registry_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_registry_root(Path(tmp))

            registry = load_registry(root)

            self.assertEqual(set(registry.entries), MODEL_NAMES)
            for name in ("research", "manuscript", "issue"):
                entry = registry.entries[name]
                self.assertEqual(entry.document_kind, "index")
                self.assertEqual(entry.dependency_profile, "dependency-v1")
                self.assertEqual(set(entry.record_sets), {"sample"})
                record_set = entry.record_sets["sample"]
                self.assertIsInstance(record_set, RecordSetEntry)
                self.assertEqual(record_set.name, "sample")
                self.assertEqual(record_set.id_pattern, r"^TST-[0-9]{4,}$")
                self.assertEqual(
                    record_set.hash_excluded_paths,
                    ("/metadata/updated_at",),
                )
                self.assertTrue(record_set.schema_path.is_file())
                self.assertTrue(record_set.path_prefix.is_relative_to(root))

    def test_index_entry_requires_complete_known_fields(self) -> None:
        mutations = {
            "document_kind": lambda entry: entry.pop("document_kind"),
            "record_sets": lambda entry: entry.pop("record_sets"),
            "empty record_sets": lambda entry: entry.__setitem__("record_sets", {}),
            "dependency_profile": lambda entry: entry.pop("dependency_profile"),
            "wrong dependency profile": lambda entry: entry.__setitem__(
                "dependency_profile", "unknown"
            ),
            "unknown entry field": lambda entry: entry.__setitem__("dependecy_profile", "typo"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = self.make_registry_root(Path(tmp))
                document = self.read_registry(root)
                mutate(document["models"]["research"])
                self.write_registry(root, document)

                with self.assertRaisesRegex(SchemaDefinitionError, "registry.invalid"):
                    load_registry(root)

    def test_record_set_rejects_missing_unknown_and_invalid_fields(self) -> None:
        mutations = {
            "missing schema": lambda value: value.pop("schema"),
            "missing path": lambda value: value.pop("path_prefix"),
            "missing id": lambda value: value.pop("id_pattern"),
            "unknown": lambda value: value.__setitem__("path_prefx", "typo"),
            "invalid regex": lambda value: value.__setitem__("id_pattern", "["),
            "invalid exclusion": lambda value: value.__setitem__(
                "hash_excluded_paths", ["not-a-pointer"]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = self.make_registry_root(Path(tmp))
                document = self.read_registry(root)
                mutate(document["models"]["research"]["record_sets"]["sample"])
                self.write_registry(root, document)

                with self.assertRaisesRegex(SchemaDefinitionError, "registry."):
                    load_registry(root)

    def test_record_schema_and_path_prefix_cannot_escape_managed_roots(self) -> None:
        cases = (
            ("schema", "/tmp/record.schema.json"),
            ("schema", "../record.schema.json"),
            ("path_prefix", "/tmp/records/"),
            ("path_prefix", "../records/"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = self.make_registry_root(Path(tmp))
                document = self.read_registry(root)
                document["models"]["research"]["record_sets"]["sample"][field] = value
                self.write_registry(root, document)

                with self.assertRaisesRegex(SchemaDefinitionError, "registry.path"):
                    load_registry(root)

    def test_schema_symlinks_cannot_escape_managed_schema_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_registry_root(Path(tmp))
            outside = root / "outside.schema.json"
            outside.write_text('{"type":"object"}\n', encoding="utf-8")
            escaped = self.schema_dir(root) / "escaped.schema.json"
            escaped.symlink_to(outside)
            document = self.read_registry(root)
            document["models"]["research"]["record_sets"]["sample"]["schema"] = escaped.name
            self.write_registry(root, document)

            with self.assertRaisesRegex(SchemaDefinitionError, "registry.path"):
                load_registry(root)

    def test_path_prefix_symlinks_cannot_escape_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = self.make_registry_root(Path(tmp))
            link = root / "escaped-records"
            link.symlink_to(Path(outside), target_is_directory=True)
            document = self.read_registry(root)
            document["models"]["research"]["record_sets"]["sample"][
                "path_prefix"
            ] = "escaped-records/"
            self.write_registry(root, document)

            with self.assertRaisesRegex(SchemaDefinitionError, "registry.path"):
                load_registry(root)

    def test_shared_model_index_schema_accepts_empty_and_populated_index(self) -> None:
        schema = load_document(SCHEMA_DIR / "model-index.schema.json")
        document = self.valid_index()

        self.assertEqual(validate_schema(document, schema), [])
        with_row = dict(document)
        with_row["records"] = [
            {
                "id": "CLM-0001",
                "record_type": "claim",
                "document": "_paperops/model/research/claims/CLM-0001.yml",
                "expected_revision": 1,
                "expected_hash": "sha256:" + "a" * 64,
            }
        ]
        self.assertEqual(validate_schema(with_row, schema), [])
        missing_hash = json.loads(json.dumps(with_row))
        del missing_hash["records"][0]["expected_hash"]
        self.assertEqual(
            [(finding.code, finding.pointer) for finding in validate_schema(missing_hash, schema)],
            [("schema.required", "/records/0/expected_hash")],
        )
        invalid = dict(document)
        invalid["unknown"] = True
        self.assertEqual(
            [
                (finding.code, finding.pointer)
                for finding in validate_schema(invalid, schema)
            ],
            [("schema.additional", "/unknown")],
        )

    def test_shared_model_index_schema_rejects_nested_unknown_and_invalid_hash(self) -> None:
        schema = load_document(SCHEMA_DIR / "model-index.schema.json")
        cases = {
            "nested unknown": ("unknown", True, "schema.additional", "/records/0/unknown"),
            "invalid hash": (
                "expected_hash",
                "sha256:not-a-hash",
                "schema.pattern",
                "/records/0/expected_hash",
            ),
        }
        for label, (field, value, code, pointer) in cases.items():
            with self.subTest(label=label):
                document = self.valid_index(with_record=True)
                document["records"][0][field] = value

                self.assertEqual(
                    [
                        (finding.code, finding.pointer)
                        for finding in validate_schema(document, schema)
                    ],
                    [(code, pointer)],
                )

    def test_shared_model_index_schema_rejects_metadata_unknown_and_missing(self) -> None:
        schema = load_document(SCHEMA_DIR / "model-index.schema.json")
        cases = {
            "unknown": ("schema.additional", "/metadata/unknown"),
            "missing": ("schema.required", "/metadata/updated_at"),
        }
        for label, expected in cases.items():
            with self.subTest(label=label):
                document = self.valid_index()
                if label == "unknown":
                    document["metadata"]["unknown"] = True
                else:
                    del document["metadata"]["updated_at"]

                self.assertEqual(
                    [
                        (finding.code, finding.pointer)
                        for finding in validate_schema(document, schema)
                    ],
                    [expected],
                )

    def test_shared_model_index_schema_requires_every_top_level_field(self) -> None:
        schema = load_document(SCHEMA_DIR / "model-index.schema.json")
        for field in (
            "model_name",
            "schema_version",
            "index_revision",
            "records",
            "extensions",
            "metadata",
        ):
            with self.subTest(field=field):
                document = self.valid_index()
                del document[field]

                self.assertEqual(
                    [
                        (finding.code, finding.pointer)
                        for finding in validate_schema(document, schema)
                    ],
                    [("schema.required", f"/{field}")],
                )

    def test_shared_model_index_schema_rejects_representative_wrong_types(self) -> None:
        schema = load_document(SCHEMA_DIR / "model-index.schema.json")
        cases = {
            "model_name": 1,
            "schema_version": True,
            "index_revision": "1",
            "records": {},
            "extensions": [],
            "metadata": [],
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                document = self.valid_index()
                document[field] = value

                self.assertEqual(
                    [
                        (finding.code, finding.pointer)
                        for finding in validate_schema(document, schema)
                    ],
                    [("schema.type", f"/{field}")],
                )

    def make_registry_root(self, root: Path) -> Path:
        schema_dir = self.schema_dir(root)
        schema_dir.parent.mkdir(parents=True)
        shutil.copytree(SCHEMA_DIR, schema_dir)
        for filename in (
            "temporary-index.schema.json",
            "temporary-record.schema.json",
            "temporary-publication.schema.json",
        ):
            (schema_dir / filename).write_text('{"type":"object"}\n', encoding="utf-8")
        self.write_registry(root, self.six_entry_registry())
        return root

    def six_entry_registry(self) -> dict[str, object]:
        aggregate = {
            "schema_version": 1,
            "authority": "project-owned",
            "hash_profile": "semantic-v1",
            "hash_excluded_paths": ["/metadata/updated_at"],
        }
        models: dict[str, object] = {
            "editorial": {
                **aggregate,
                "schema": "editorial-model.schema.json",
                "default_path": "_paperops/model/editorial/editorial-model.yml",
            },
            "results_hierarchy": {
                **aggregate,
                "schema": "results-hierarchy.schema.json",
                "default_path": "_paperops/model/editorial/results-hierarchy.yml",
                "hash_excluded_paths": [],
            },
            "publication": {
                **aggregate,
                "document_kind": "aggregate",
                "schema": "temporary-publication.schema.json",
                "default_path": "_paperops/model/publication/publication-model.yml",
            },
        }
        for name, directory in (
            ("research", "research"),
            ("manuscript", "manuscript"),
            ("issue", "issues"),
        ):
            models[name] = {
                **aggregate,
                "document_kind": "index",
                "schema": "temporary-index.schema.json",
                "default_path": f"_paperops/model/{directory}/index.yml",
                "record_sets": {
                    "sample": {
                        "schema": "temporary-record.schema.json",
                        "path_prefix": f"_paperops/model/{directory}/records/",
                        "id_pattern": r"^TST-[0-9]{4,}$",
                        "hash_excluded_paths": ["/metadata/updated_at"],
                    }
                },
                "dependency_profile": "dependency-v1",
            }
        return {
            "registry_version": 1,
            "validator_profile": "paperops-schema-v1",
            "models": models,
        }

    def read_registry(self, root: Path) -> dict[str, object]:
        return load_document(self.schema_dir(root) / "registry.yml")

    def write_registry(self, root: Path, document: dict[str, object]) -> None:
        (self.schema_dir(root) / "registry.yml").write_text(
            json.dumps(document), encoding="utf-8"
        )

    @staticmethod
    def schema_dir(root: Path) -> Path:
        return root / "_paperops" / "defaults" / "schemas"

    @staticmethod
    def valid_index(*, with_record: bool = False) -> dict[str, object]:
        records: list[dict[str, object]] = []
        if with_record:
            records.append(
                {
                    "id": "CLM-0001",
                    "record_type": "claim",
                    "document": "_paperops/model/research/claims/CLM-0001.yml",
                    "expected_revision": 1,
                    "expected_hash": "sha256:" + "a" * 64,
                }
            )
        return {
            "model_name": "research",
            "schema_version": 1,
            "index_revision": 1,
            "records": records,
            "extensions": {},
            "metadata": {"updated_at": ""},
        }


if __name__ == "__main__":
    unittest.main()
