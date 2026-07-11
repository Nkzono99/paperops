"""Safe document loading and schema utilities for PaperOps models."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"


class DocumentLoadError(ValueError):
    pass


class SchemaDefinitionError(ValueError):
    pass


SUPPORTED_KEYWORDS = frozenset(
    {
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "enum",
        "const",
        "pattern",
        "minLength",
        "$defs",
        "$ref",
        "allOf",
        "anyOf",
        "oneOf",
    }
)


def _mapping_without_duplicates(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise DocumentLoadError(f"document.duplicate_key: {key!r}")
        mapping[key] = value
    return mapping


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise DocumentLoadError("document.non_finite: non-finite number")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(key)
            _reject_non_finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_non_finite(item)


def load_document(path: Path) -> Any:
    """Load JSON/YAML, rejecting duplicate keys and non-finite numbers."""
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text, object_pairs_hook=_mapping_without_duplicates)
    except DocumentLoadError:
        raise
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as error:
            raise DocumentLoadError(
                "document.yaml_unavailable: PyYAML is required for YAML documents"
            ) from error

        class DuplicateKeySafeLoader(yaml.SafeLoader):
            pass

        def construct_mapping(
            loader: DuplicateKeySafeLoader,
            node: Any,
            deep: bool = False,
        ) -> dict[Any, Any]:
            loader.flatten_mapping(node)
            pairs = loader.construct_pairs(node, deep=deep)
            return _mapping_without_duplicates(pairs)

        DuplicateKeySafeLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping,
        )
        document = yaml.load(text, Loader=DuplicateKeySafeLoader)

    _reject_non_finite(document)
    return document


def _escape_pointer_token(token: Any) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _child_pointer(pointer: str, token: Any) -> str:
    return f"{pointer}/{_escape_pointer_token(token)}"


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _walk_schema_definition(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise SchemaDefinitionError("schema.invalid_definition: schema must be an object")
    for keyword in schema:
        if keyword not in SUPPORTED_KEYWORDS:
            raise SchemaDefinitionError(
                f"schema.unsupported_keyword: unsupported keyword {keyword!r}"
            )
    reference = schema.get("$ref")
    if reference is not None and (
        not isinstance(reference, str) or not reference.startswith("#/$defs/")
    ):
        raise SchemaDefinitionError(
            f"schema.remote_ref: only local #/$defs references are supported: {reference!r}"
        )
    for container in ("properties", "$defs"):
        children = schema.get(container, {})
        if not isinstance(children, dict):
            raise SchemaDefinitionError(
                f"schema.invalid_definition: {container} must be an object"
            )
        for child in children.values():
            _walk_schema_definition(child)
    for keyword in ("items", "additionalProperties"):
        child = schema.get(keyword)
        if isinstance(child, dict):
            _walk_schema_definition(child)
    for keyword in ("allOf", "anyOf", "oneOf"):
        children = schema.get(keyword, [])
        if not isinstance(children, list):
            raise SchemaDefinitionError(
                f"schema.invalid_definition: {keyword} must be an array"
            )
        for child in children:
            _walk_schema_definition(child)


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    current: Any = root_schema
    for raw_token in reference[2:].split("/"):
        token = _decode_pointer_token(raw_token)
        if not isinstance(current, dict) or token not in current:
            raise SchemaDefinitionError(
                f"schema.invalid_ref: local reference does not exist: {reference}"
            )
        current = current[token]
    if not isinstance(current, dict):
        raise SchemaDefinitionError(
            f"schema.invalid_ref: local reference is not a schema: {reference}"
        )
    return current


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _json_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def _finding(code: str, pointer: str, message: str) -> ModelFinding:
    return ModelFinding(code=code, pointer=pointer, message=message)


def _validate_value(
    document: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    pointer: str,
) -> list[ModelFinding]:
    findings: list[ModelFinding] = []

    reference = schema.get("$ref")
    if isinstance(reference, str):
        findings.extend(
            _validate_value(document, _resolve_ref(root_schema, reference), root_schema, pointer)
        )

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(
            isinstance(expected, str) and _matches_type(document, expected)
            for expected in expected_types
        ):
            return findings + [
                _finding("schema.type", pointer, f"expected type {expected_type!r}")
            ]

    if "enum" in schema and not any(
        _json_equal(document, candidate) for candidate in schema["enum"]
    ):
        findings.append(_finding("schema.enum", pointer, "value is not in enum"))
    if "const" in schema and not _json_equal(document, schema["const"]):
        findings.append(_finding("schema.const", pointer, "value does not match const"))

    if isinstance(document, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in document:
                findings.append(
                    _finding(
                        "schema.required",
                        _child_pointer(pointer, name),
                        f"required property {name!r} is missing",
                    )
                )
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, value in document.items():
            child_pointer = _child_pointer(pointer, name)
            if name in properties:
                findings.extend(
                    _validate_value(value, properties[name], root_schema, child_pointer)
                )
            elif additional is False:
                findings.append(
                    _finding(
                        "schema.additional",
                        child_pointer,
                        f"additional property {name!r} is not allowed",
                    )
                )
            elif isinstance(additional, dict):
                findings.extend(
                    _validate_value(value, additional, root_schema, child_pointer)
                )

    if isinstance(document, list):
        if "minItems" in schema and len(document) < schema["minItems"]:
            findings.append(_finding("schema.min_items", pointer, "array is too short"))
        if "maxItems" in schema and len(document) > schema["maxItems"]:
            findings.append(_finding("schema.max_items", pointer, "array is too long"))
        if schema.get("uniqueItems"):
            for index, item in enumerate(document):
                if any(_json_equal(item, previous) for previous in document[:index]):
                    findings.append(
                        _finding(
                            "schema.unique_items",
                            _child_pointer(pointer, index),
                            "array item is not unique",
                        )
                    )
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(document):
                findings.extend(
                    _validate_value(
                        item,
                        item_schema,
                        root_schema,
                        _child_pointer(pointer, index),
                    )
                )

    if isinstance(document, str):
        if "minLength" in schema and len(document) < schema["minLength"]:
            findings.append(_finding("schema.min_length", pointer, "string is too short"))
        if "pattern" in schema and re.search(schema["pattern"], document) is None:
            findings.append(
                _finding("schema.pattern", pointer, "string does not match pattern")
            )

    for branch in schema.get("allOf", []):
        findings.extend(_validate_value(document, branch, root_schema, pointer))
    if "anyOf" in schema and not any(
        not _validate_value(document, branch, root_schema, pointer)
        for branch in schema["anyOf"]
    ):
        findings.append(
            _finding("schema.any_of", pointer, "no anyOf branch matched")
        )
    if "oneOf" in schema:
        matches = sum(
            not _validate_value(document, branch, root_schema, pointer)
            for branch in schema["oneOf"]
        )
        if matches != 1:
            findings.append(
                _finding("schema.one_of", pointer, "exactly one oneOf branch must match")
            )
    return findings


def validate_schema(
    document: Any,
    schema: dict[str, Any],
) -> list[ModelFinding]:
    """Validate a document against PaperOps Schema Profile v1."""
    _walk_schema_definition(schema)
    return _validate_value(document, schema, schema, "")


def _normalize_for_hash(
    value: Any,
    excluded_paths: frozenset[str],
    pointer: str,
) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("hash.non_finite: non-finite number")
    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            child_pointer = _child_pointer(pointer, key)
            if child_pointer in excluded_paths:
                continue
            normalized[key] = _normalize_for_hash(
                item,
                excluded_paths,
                child_pointer,
            )
        return normalized
    if isinstance(value, (list, tuple)):
        normalized_items: list[Any] = []
        for index, item in enumerate(value):
            child_pointer = _child_pointer(pointer, index)
            if child_pointer in excluded_paths:
                continue
            normalized_items.append(
                _normalize_for_hash(item, excluded_paths, child_pointer)
            )
        return normalized_items
    return value


def _canonical_bytes_at_pointer(
    value: Any,
    *,
    excluded_paths: tuple[str, ...],
    pointer: str,
) -> bytes:
    normalized = _normalize_for_hash(value, frozenset(excluded_paths), pointer)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_bytes(
    value: Any,
    *,
    excluded_paths: tuple[str, ...] = (),
) -> bytes:
    """Serialize a semantic value to deterministic UTF-8 JSON bytes."""
    return _canonical_bytes_at_pointer(
        value,
        excluded_paths=excluded_paths,
        pointer="",
    )


def _select_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise KeyError(pointer)
    current = value
    for raw_token in pointer[1:].split("/"):
        token = _decode_pointer_token(raw_token)
        try:
            if isinstance(current, list):
                if token == "-" or not token.isdigit():
                    raise KeyError(pointer)
                current = current[int(token)]
            elif isinstance(current, dict):
                current = current[token]
            else:
                raise KeyError(pointer)
        except (IndexError, KeyError) as error:
            raise KeyError(pointer) from error
    return current


def semantic_hash(
    value: Any,
    *,
    excluded_paths: tuple[str, ...] = (),
    pointer: str = "",
) -> str:
    """Return the canonical SHA-256 hash of a value or selected subrecord."""
    selected = _select_pointer(value, pointer)
    payload = _canonical_bytes_at_pointer(
        selected,
        excluded_paths=excluded_paths,
        pointer=pointer,
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()
