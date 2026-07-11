from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT


SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paperops_models import build_object_catalog, load_model_document  # noqa: E402
from paperops_schema import RecordSetEntry, RegistryEntry, semantic_hash  # noqa: E402


class PaperOpsModelCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.schema_dir = self.root / "schemas"
        self.schema_dir.mkdir()
        self.index_schema = self.schema_dir / "index.schema.json"
        self.record_schema = self.schema_dir / "record.schema.json"
        self.aggregate_schema = self.schema_dir / "aggregate.schema.json"
        self.write_json(self.index_schema, {"type": "object"})
        self.write_json(
            self.record_schema,
            {
                "type": "object",
                "required": ["id", "record_type", "revision", "metadata"],
                "properties": {
                    "id": {"type": "string"},
                    "record_type": {"const": "claim"},
                    "revision": {"type": "integer"},
                    "metadata": {
                        "type": "object",
                        "required": ["updated_at"],
                        "properties": {"updated_at": {"type": "string"}},
                        "additionalProperties": False,
                    },
                },
                "additionalProperties": False,
            },
        )
        self.write_json(self.aggregate_schema, {"type": "object"})
        self.records_dir = self.root / "model" / "research" / "claims"
        self.records_dir.mkdir(parents=True)
        self.index_path = self.root / "model" / "research" / "index.yml"
        self.entry = RegistryEntry(
            name="research",
            schema_path=self.index_schema,
            schema_version=1,
            authority="project-owned",
            default_path=self.index_path,
            hash_profile="semantic-v1",
            hash_excluded_paths=("/metadata/updated_at",),
            document_kind="index",
            record_sets={
                "claim": RecordSetEntry(
                    name="claim",
                    schema_path=self.record_schema,
                    path_prefix=self.records_dir,
                    id_pattern=r"^CLM-[0-9]{4,}$",
                    hash_excluded_paths=("/metadata/updated_at",),
                ),
                "other": RecordSetEntry(
                    name="other",
                    schema_path=self.record_schema,
                    path_prefix=self.records_dir,
                    id_pattern=r"^CLM-[0-9]{4,}$",
                    hash_excluded_paths=("/metadata/updated_at",),
                ),
            },
            dependency_profile="dependency-v1",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def record(self, record_id: str = "CLM-0001") -> dict[str, object]:
        return {
            "id": record_id,
            "record_type": "claim",
            "revision": 1,
            "metadata": {"updated_at": "2026-07-11"},
        }

    def row(self, document: str, record: dict[str, object]) -> dict[str, object]:
        return {
            "id": record["id"],
            "record_type": record["record_type"],
            "document": document,
            "expected_revision": record["revision"],
            "expected_hash": semantic_hash(
                record, excluded_paths=("/metadata/updated_at",)
            ),
        }

    def write_index(self, rows: list[dict[str, object]]) -> None:
        self.write_json(
            self.index_path,
            {
                "model_name": "research",
                "schema_version": 1,
                "index_revision": 1,
                "records": rows,
                "extensions": {},
                "metadata": {"updated_at": "2026-07-11"},
            },
        )

    def load_one(self):
        return load_model_document(self.root, self.entry)

    def test_safe_row_selects_record_schema_and_registers_object(self) -> None:
        record = self.record()
        path = self.records_dir / "CLM-0001.yml"
        self.write_json(path, record)
        self.write_index([self.row("model/research/claims/CLM-0001.yml", record)])

        model = self.load_one()
        catalog = build_object_catalog([model])

        self.assertEqual(model.findings, [])
        self.assertEqual(len(model.records), 1)
        self.assertEqual(model.records[0].record_type, "claim")
        self.assertEqual(catalog.objects["CLM-0001"].revision, 1)
        self.assertEqual(catalog.objects["CLM-0001"].object_hash, self.row("x", record)["expected_hash"])

    def test_row_record_mismatches_have_distinct_codes_and_pointers(self) -> None:
        mutations = {
            "id": ("CLM-9999", "index.id", "/records/0/id"),
            "record_type": ("other", "index.type", "/records/0/record_type"),
            "expected_revision": (2, "index.revision", "/records/0/expected_revision"),
            "expected_hash": ("sha256:" + "0" * 64, "index.hash", "/records/0/expected_hash"),
        }
        for field, (value, code, pointer) in mutations.items():
            with self.subTest(field=field):
                record = self.record()
                row = self.row("model/research/claims/CLM-0001.yml", record)
                row[field] = value
                path = self.records_dir / "CLM-0001.yml"
                self.write_json(path, record)
                self.write_index([row])

                model = self.load_one()

                self.assertIn((code, pointer), [(f.code, f.pointer) for f in model.findings])
                self.assertEqual(model.records, ())

    def test_unknown_record_type_is_rejected_before_loading(self) -> None:
        record = self.record()
        row = self.row("model/research/claims/CLM-0001.yml", record)
        row["record_type"] = "unknown"
        self.write_index([row])

        model = self.load_one()

        self.assertEqual(
            [(f.code, f.pointer) for f in model.findings],
            [("reference.type", "/records/0/record_type")],
        )

    def test_duplicate_ids_are_rejected_within_index_and_across_catalog(self) -> None:
        record = self.record()
        path = self.records_dir / "CLM-0001.yml"
        self.write_json(path, record)
        row = self.row("model/research/claims/CLM-0001.yml", record)
        self.write_index([row, row])
        within = self.load_one()
        self.assertIn(
            ("reference.duplicate", "/records/1/id"),
            [(f.code, f.pointer) for f in within.findings],
        )

        self.write_index([row])
        first = self.load_one()
        second = self.load_one()
        catalog = build_object_catalog([first, second])
        self.assertIn("reference.duplicate", [f.code for f in catalog.findings])
        self.assertNotIn("CLM-0001", catalog.objects)

    def test_missing_and_unreadable_records_are_distinct(self) -> None:
        record = self.record()
        row = self.row("model/research/claims/CLM-0001.yml", record)
        self.write_index([row])
        missing = self.load_one()
        self.assertIn(
            ("reference.document", "/records/0/document"),
            [(f.code, f.pointer) for f in missing.findings],
        )

        (self.records_dir / "CLM-0001.yml").write_text("[broken", encoding="utf-8")
        unreadable = self.load_one()
        self.assertIn(
            ("document.non_json", "/records/0/document"),
            [(f.code, f.pointer) for f in unreadable.findings],
        )

    def test_posix_windows_and_symlink_escapes_are_rejected(self) -> None:
        record = self.record()
        for value in (
            "../outside.yml",
            r"C:\\outside.yml",
            r"..\\outside.yml",
            "model/research/results/CLM-0001.yml",
        ):
            with self.subTest(value=value):
                self.write_index([self.row(value, record)])
                model = self.load_one()
                self.assertEqual(
                    [(f.code, f.pointer) for f in model.findings],
                    [("reference.path", "/records/0/document")],
                )

        outside = self.root / "outside.yml"
        self.write_json(outside, record)
        link = self.records_dir / "CLM-0001.yml"
        link.symlink_to(outside)
        self.write_index([self.row("model/research/claims/CLM-0001.yml", record)])
        model = self.load_one()
        self.assertEqual(
            [(f.code, f.pointer) for f in model.findings],
            [("reference.path", "/records/0/document")],
        )

    def test_orphan_symlink_escape_is_a_path_error_not_an_orphan(self) -> None:
        outside = self.root / "outside.yml"
        self.write_json(outside, self.record())
        (self.records_dir / "escaped.yml").symlink_to(outside)
        self.write_index([])

        model = self.load_one()

        self.assertEqual(
            [(f.code, f.pointer) for f in model.findings],
            [("reference.path", "/records")],
        )

    def test_orphan_is_warning_or_strict_error(self) -> None:
        self.write_json(self.records_dir / "CLM-0001.yml", self.record())
        self.write_index([])

        advisory = load_model_document(self.root, self.entry)
        strict = load_model_document(self.root, self.entry, strict=True)

        self.assertEqual(
            [(f.code, f.severity) for f in advisory.findings],
            [("reference.orphan", "warning")],
        )
        self.assertEqual(
            [(f.code, f.severity) for f in strict.findings],
            [("reference.orphan", "error")],
        )

    def test_schema_failed_record_is_excluded_from_catalog(self) -> None:
        invalid = self.record()
        invalid["unexpected"] = True
        path = self.records_dir / "CLM-0001.yml"
        self.write_json(path, invalid)
        self.write_index([self.row("model/research/claims/CLM-0001.yml", invalid)])

        model = self.load_one()
        catalog = build_object_catalog([model])

        self.assertIn(
            ("schema.additional", "/records/0/document/unexpected"),
            [(f.code, f.pointer) for f in model.findings],
        )
        self.assertEqual(model.records, ())
        self.assertEqual(catalog.objects, {})

if __name__ == "__main__":
    unittest.main()
