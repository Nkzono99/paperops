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


@dataclass(frozen=True)
class RegistryEntry:
    name: str
    schema_path: Path
    schema_version: int
    authority: str
    default_path: Path
    hash_profile: str
    hash_excluded_paths: tuple[str, ...]


@dataclass(frozen=True)
class SchemaRegistry:
    version: int
    validator_profile: str
    entries: dict[str, RegistryEntry]


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


def _registry_error(code: str, message: str) -> SchemaDefinitionError:
    return SchemaDefinitionError(f"registry.{code}: {message}")


def _registry_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _registry_error("invalid", f"{field} must be an object with string keys")
    return value


def _registry_string(entry: dict[str, Any], field: str, model: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise _registry_error("invalid", f"models.{model}.{field} must be a string")
    return value


def _resolve_registry_schema(registry_dir: Path, raw_path: str, model: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute() or len(relative.parts) != 1 or relative.name != raw_path:
        raise _registry_error("path", f"models.{model}.schema must be a filename")
    resolved = (registry_dir / relative).resolve()
    if resolved.parent != registry_dir or not resolved.is_file():
        if resolved.parent != registry_dir:
            raise _registry_error("path", f"models.{model}.schema escapes the registry")
        raise _registry_error("schema_missing", f"schema file is missing: {raw_path}")
    return resolved


def _resolve_registry_default(root: Path, raw_path: str, model: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise _registry_error("path", f"models.{model}.default_path must stay within root")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise _registry_error("path", f"models.{model}.default_path escapes root")
    return resolved


def load_registry(root: Path) -> SchemaRegistry:
    """Load and validate the managed schema registry below a project root."""
    resolved_root = root.resolve()
    registry_dir = resolved_root / "_paperops" / "defaults" / "schemas"
    registry_path = registry_dir / "registry.yml"
    try:
        document = load_document(registry_path)
    except (OSError, DocumentLoadError) as error:
        raise _registry_error("invalid", f"cannot load {registry_path}: {error}") from error
    registry = _registry_mapping(document, "registry")

    version = registry.get("registry_version")
    if version != 1 or isinstance(version, bool):
        raise _registry_error("version", f"unsupported registry_version: {version!r}")
    validator_profile = registry.get("validator_profile")
    if validator_profile != "paperops-schema-v1":
        raise _registry_error(
            "profile",
            f"unsupported validator_profile: {validator_profile!r}",
        )

    models = _registry_mapping(registry.get("models"), "models")
    entries: dict[str, RegistryEntry] = {}
    for name, raw_entry in models.items():
        entry = _registry_mapping(raw_entry, f"models.{name}")
        schema_version = entry.get("schema_version")
        if (
            not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version < 1
        ):
            raise _registry_error(
                "invalid",
                f"models.{name}.schema_version must be a positive integer",
            )
        authority = _registry_string(entry, "authority", name)
        if authority != "project-owned":
            raise _registry_error("invalid", f"unsupported authority: {authority!r}")
        hash_profile = _registry_string(entry, "hash_profile", name)
        if hash_profile != "semantic-v1":
            raise _registry_error("invalid", f"unsupported hash_profile: {hash_profile!r}")
        raw_exclusions = entry.get("hash_excluded_paths", [])
        if not isinstance(raw_exclusions, list) or not all(
            isinstance(pointer, str) and pointer.startswith("/")
            for pointer in raw_exclusions
        ):
            raise _registry_error(
                "invalid",
                f"models.{name}.hash_excluded_paths must be JSON Pointer strings",
            )
        entries[name] = RegistryEntry(
            name=name,
            schema_path=_resolve_registry_schema(
                registry_dir,
                _registry_string(entry, "schema", name),
                name,
            ),
            schema_version=schema_version,
            authority=authority,
            default_path=_resolve_registry_default(
                resolved_root,
                _registry_string(entry, "default_path", name),
                name,
            ),
            hash_profile=hash_profile,
            hash_excluded_paths=tuple(raw_exclusions),
        )
    return SchemaRegistry(
        version=version,
        validator_profile=validator_profile,
        entries=entries,
    )


def _escape_pointer_token(token: Any) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _child_pointer(pointer: str, token: Any) -> str:
    return f"{pointer}/{_escape_pointer_token(token)}"


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _invalid_definition(keyword: str, expectation: str) -> SchemaDefinitionError:
    return SchemaDefinitionError(
        f"schema.invalid_definition: {keyword} {expectation}"
    )


def _is_non_negative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _walk_schema_definition(schema: Any) -> None:
    if not isinstance(schema, dict):
        raise SchemaDefinitionError("schema.invalid_definition: schema must be an object")
    for keyword in schema:
        if keyword not in SUPPORTED_KEYWORDS:
            raise SchemaDefinitionError(
                f"schema.unsupported_keyword: unsupported keyword {keyword!r}"
            )

    for keyword in ("$schema", "$id", "title", "description"):
        if keyword in schema and not isinstance(schema[keyword], str):
            raise _invalid_definition(keyword, "must be a string")

    if "type" in schema:
        expected_type = schema["type"]
        if isinstance(expected_type, str):
            expected_types = [expected_type]
        elif isinstance(expected_type, list) and all(
            isinstance(item, str) for item in expected_type
        ):
            expected_types = expected_type
        else:
            raise _invalid_definition("type", "must be a string or array of strings")
        known_types = {"object", "array", "string", "integer", "number", "boolean", "null"}
        if not expected_types or any(item not in known_types for item in expected_types):
            raise _invalid_definition("type", "contains an unsupported type")

    if "required" in schema and (
        not isinstance(schema["required"], list)
        or not all(isinstance(item, str) for item in schema["required"])
    ):
        raise _invalid_definition("required", "must be an array of strings")

    for keyword in ("properties", "$defs"):
        if keyword in schema and (
            not isinstance(schema[keyword], dict)
            or not all(isinstance(name, str) for name in schema[keyword])
        ):
            raise _invalid_definition(keyword, "must be an object with string keys")

    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"],
        (bool, dict),
    ):
        raise _invalid_definition(
            "additionalProperties",
            "must be a boolean or schema object",
        )
    if "items" in schema and not isinstance(schema["items"], dict):
        raise _invalid_definition("items", "must be a schema object")
    for keyword in ("minItems", "maxItems", "minLength"):
        if keyword in schema and not _is_non_negative_integer(schema[keyword]):
            raise _invalid_definition(keyword, "must be a non-negative integer")
    if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
        raise _invalid_definition("uniqueItems", "must be a boolean")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise _invalid_definition("enum", "must be an array")
    if "pattern" in schema:
        pattern = schema["pattern"]
        if not isinstance(pattern, str):
            raise _invalid_definition("pattern", "must be a string")
        try:
            re.compile(pattern)
        except re.error as error:
            raise _invalid_definition("pattern", f"is not a valid regex: {error}") from error

    reference = schema.get("$ref")
    if reference is not None and not isinstance(reference, str):
        raise _invalid_definition("$ref", "must be a string")
    if isinstance(reference, str) and not reference.startswith("#/$defs/"):
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
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
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
