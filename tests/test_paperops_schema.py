from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from paperops_schema import (  # noqa: E402
    DocumentLoadError,
    SchemaDefinitionError,
    canonical_bytes,
    load_document,
    semantic_hash,
    validate_schema,
)


class DocumentLoaderTest(unittest.TestCase):
    def test_loader_rejects_duplicate_yaml_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.yml"
            path.write_text(
                "schema_version: 1\nschema_version: 2\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DocumentLoadError, "document.duplicate_key"):
                load_document(path)

    def test_loader_rejects_non_finite_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.yml"
            path.write_text("score: .nan\n", encoding="utf-8")

            with self.assertRaisesRegex(DocumentLoadError, "document.non_finite"):
                load_document(path)


class SchemaProfileTest(unittest.TestCase):
    def test_required_property_reports_property_pointer(self) -> None:
        findings = validate_schema(
            {},
            {"type": "object", "required": ["name"]},
        )

        self.assertEqual(
            [(finding.code, finding.pointer) for finding in findings],
            [("schema.required", "/name")],
        )

    def test_type_mismatch_reports_root_pointer(self) -> None:
        findings = validate_schema({}, {"type": "array"})

        self.assertEqual(
            [(finding.code, finding.pointer) for finding in findings],
            [("schema.type", "")],
        )

    def test_additional_property_reports_property_pointer(self) -> None:
        findings = validate_schema(
            {"name": "ok", "extra": 1},
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": False,
            },
        )

        self.assertEqual(
            [(finding.code, finding.pointer) for finding in findings],
            [("schema.additional", "/extra")],
        )

    def test_local_ref_resolves_definition(self) -> None:
        findings = validate_schema(
            "ok",
            {
                "$defs": {"item": {"type": "string"}},
                "$ref": "#/$defs/item",
            },
        )

        self.assertEqual(findings, [])

    def test_remote_ref_is_rejected(self) -> None:
        with self.assertRaisesRegex(SchemaDefinitionError, "schema.remote_ref"):
            validate_schema("ok", {"$ref": "https://example.invalid/schema"})

    def test_unsupported_keyword_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            SchemaDefinitionError,
            "schema.unsupported_keyword",
        ):
            validate_schema("ok", {"if": {"type": "string"}})

    def test_one_of_requires_exactly_one_successful_branch(self) -> None:
        schema = {"oneOf": [{"type": "integer"}, {"type": "string"}]}

        self.assertEqual(validate_schema(1, schema), [])
        self.assertEqual(validate_schema("one", schema), [])
        findings = validate_schema([], schema)
        self.assertEqual(
            [(finding.code, finding.pointer) for finding in findings],
            [("schema.one_of", "")],
        )

    def test_additional_property_subschema_validates_unknown_value(self) -> None:
        findings = validate_schema(
            {"known": "ok", "extra": 1},
            {
                "type": "object",
                "properties": {"known": {"type": "string"}},
                "additionalProperties": {"type": "string"},
            },
        )

        self.assertEqual(
            [(finding.code, finding.pointer) for finding in findings],
            [("schema.type", "/extra")],
        )

    def test_enum_distinguishes_nested_booleans_from_numbers(self) -> None:
        schema = {"enum": [{"x": True}, [True]]}

        for document in ({"x": 1}, [1]):
            with self.subTest(document=document):
                findings = validate_schema(document, schema)
                self.assertEqual([finding.code for finding in findings], ["schema.enum"])

    def test_const_distinguishes_nested_booleans_from_numbers(self) -> None:
        cases = (({"x": 1}, {"x": True}), ([1], [True]))

        for document, constant in cases:
            with self.subTest(document=document):
                findings = validate_schema(document, {"const": constant})
                self.assertEqual([finding.code for finding in findings], ["schema.const"])

    def test_unique_items_distinguishes_nested_booleans_from_numbers(self) -> None:
        document = [{"x": True}, {"x": 1}, [True], [1]]

        self.assertEqual(validate_schema(document, {"uniqueItems": True}), [])

    def test_all_of_accepts_all_branches_and_reports_failed_branch(self) -> None:
        schema = {"allOf": [{"type": "integer"}, {"const": 1}]}

        self.assertEqual(validate_schema(1, schema), [])
        findings = validate_schema(2, schema)
        self.assertEqual([finding.code for finding in findings], ["schema.const"])

    def test_any_of_accepts_one_branch_and_reports_when_none_match(self) -> None:
        schema = {"anyOf": [{"type": "integer"}, {"type": "string"}]}

        self.assertEqual(validate_schema("one", schema), [])
        findings = validate_schema([], schema)
        self.assertEqual([finding.code for finding in findings], ["schema.any_of"])

    def test_invalid_keyword_value_types_are_schema_definition_errors(self) -> None:
        invalid_schemas = (
            {"type": 1},
            {"required": True},
            {"properties": []},
            {"additionalProperties": "no"},
            {"items": []},
            {"minItems": "1"},
            {"maxItems": False},
            {"uniqueItems": "yes"},
            {"enum": {}},
            {"pattern": 1},
            {"minLength": "1"},
            {"$defs": []},
            {"allOf": {}},
            {"anyOf": {}},
            {"oneOf": {}},
        )

        for schema in invalid_schemas:
            with self.subTest(schema=schema):
                with self.assertRaisesRegex(
                    SchemaDefinitionError,
                    "schema.invalid_definition",
                ):
                    validate_schema({}, schema)

    def test_invalid_pattern_is_schema_definition_error(self) -> None:
        with self.assertRaisesRegex(
            SchemaDefinitionError,
            "schema.invalid_definition",
        ):
            validate_schema("value", {"pattern": "["})


class CanonicalHashTest(unittest.TestCase):
    def test_mapping_order_does_not_change_hash(self) -> None:
        self.assertEqual(
            semantic_hash({"a": 1, "b": 2}),
            semantic_hash({"b": 2, "a": 1}),
        )
        self.assertRegex(semantic_hash({"a": 1}), r"^sha256:[0-9a-f]{64}$")

    def test_yaml_comments_and_line_endings_do_not_change_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lf_path = Path(tmp) / "lf.yml"
            crlf_path = Path(tmp) / "crlf.yml"
            lf_path.write_bytes(b"# comment\nname: paper\ncount: 1\n")
            crlf_path.write_bytes(b"name: paper\r\ncount: 1\r\n")

            self.assertEqual(
                semantic_hash(load_document(lf_path)),
                semantic_hash(load_document(crlf_path)),
            )

    def test_exclusion_matches_only_exact_path(self) -> None:
        first = {"metadata": {"updated_at": "old", "other": "same"}}
        updated_at_changed = {
            "metadata": {"updated_at": "new", "other": "same"}
        }
        other_changed = {"metadata": {"updated_at": "new", "other": "changed"}}
        exclusions = ("/metadata/updated_at",)

        self.assertEqual(
            semantic_hash(first, excluded_paths=exclusions),
            semantic_hash(updated_at_changed, excluded_paths=exclusions),
        )
        self.assertNotEqual(
            semantic_hash(first, excluded_paths=exclusions),
            semantic_hash(other_changed, excluded_paths=exclusions),
        )

    def test_array_order_changes_hash(self) -> None:
        self.assertNotEqual(semantic_hash(["a", "b"]), semantic_hash(["b", "a"]))

    def test_semantic_value_changes_hash(self) -> None:
        self.assertNotEqual(
            semantic_hash({"selected_story_id": "STORY-1"}),
            semantic_hash({"selected_story_id": "STORY-2"}),
        )

    def test_object_pointer_hashes_selected_subrecord(self) -> None:
        document = {
            "story_candidates": [
                {"id": "STORY-1", "score": 3},
                {"id": "STORY-2", "score": 2},
            ]
        }

        self.assertEqual(
            semantic_hash(document, pointer="/story_candidates/0"),
            semantic_hash(document["story_candidates"][0]),
        )

    def test_non_finite_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "hash.non_finite"):
            canonical_bytes(float("nan"))


if __name__ == "__main__":
    unittest.main()
