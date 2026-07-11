"""Load PaperOps aggregate/index models and build a schema-clean object catalog."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

from paperops_schema import (
    ModelFinding,
    RegistryEntry,
    load_document,
    semantic_hash,
    validate_document_version,
    validate_schema,
)


@dataclass(frozen=True)
class RecordDocument:
    model_name: str
    record_type: str
    path: Path
    document: dict[str, Any]
    object_id: str
    revision: int
    object_hash: str
    pointer: str


@dataclass(frozen=True)
class ModelDocument:
    entry: RegistryEntry
    path: Path
    document: Any | None
    schema_findings: tuple[ModelFinding, ...]
    records: tuple[RecordDocument, ...] = ()
    catalog_findings: tuple[ModelFinding, ...] = ()

    @property
    def schema_clean(self) -> bool:
        return self.document is not None and not self.schema_findings

    @property
    def findings(self) -> list[ModelFinding]:
        return [*self.schema_findings, *self.catalog_findings]


@dataclass(frozen=True)
class CatalogObject:
    object_id: str
    object_type: str
    model_name: str
    document: dict[str, Any]
    revision: int | None
    object_hash: str
    pointer: str


@dataclass(frozen=True)
class ObjectCatalog:
    objects: dict[str, CatalogObject]
    findings: tuple[ModelFinding, ...]


def _exception_finding(error: Exception, pointer: str) -> ModelFinding:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    if separator and "." in prefix and " " not in prefix:
        return ModelFinding(prefix, pointer, detail.strip())
    return ModelFinding("document.load", pointer, message)


def _prefix_schema_finding(finding: ModelFinding, base: str) -> ModelFinding:
    suffix = "" if finding.pointer in ("", "/") else finding.pointer
    return ModelFinding(finding.code, base + suffix, finding.message, finding.severity)


def _unsafe_relative_path(value: str) -> bool:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    return (
        not value
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or bool(windows.root)
        or ".." in posix.parts
        or ".." in windows.parts
    )


def _safe_record_path(
    root: Path,
    path_prefix: Path,
    value: Any,
) -> Path | None:
    if not isinstance(value, str) or _unsafe_relative_path(value):
        return None
    root_resolved = root.resolve()
    prefix_resolved = path_prefix.resolve()
    candidate = root / Path(value)
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    if not resolved.is_relative_to(root_resolved):
        return None
    if not resolved.is_relative_to(prefix_resolved):
        return None
    return candidate


def _load_base(entry: RegistryEntry, path: Path) -> tuple[Any | None, list[ModelFinding]]:
    try:
        document = load_document(path)
        schema = load_document(entry.schema_path)
        validate_document_version(entry, document)
        return document, validate_schema(document, schema)
    except Exception as error:
        return None, [_exception_finding(error, "/")]


def _row_value(row: Any, key: str) -> Any:
    return row.get(key) if isinstance(row, dict) else None


def _orphan_findings(
    entry: RegistryEntry,
    referenced: set[Path],
    *,
    strict: bool,
) -> list[ModelFinding]:
    findings: list[ModelFinding] = []
    severity = "error" if strict else "warning"
    scanned_prefixes: set[Path] = set()
    for record_set in entry.record_sets.values():
        prefix = record_set.path_prefix
        resolved_prefix = prefix.resolve()
        if resolved_prefix in scanned_prefixes or not prefix.is_dir():
            continue
        scanned_prefixes.add(resolved_prefix)
        for candidate in sorted(prefix.rglob("*")):
            if (
                candidate.absolute() in referenced
                or candidate.resolve(strict=False) in referenced
            ):
                continue
            if candidate.is_symlink():
                resolved = candidate.resolve(strict=False)
                if not resolved.is_relative_to(prefix.resolve()):
                    findings.append(
                        ModelFinding(
                            "reference.path",
                            "/records",
                            f"record symlink escapes its registered path prefix: {candidate}",
                        )
                    )
                continue
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".json", ".yml", ".yaml"}:
                continue
            findings.append(
                ModelFinding(
                    "reference.orphan",
                    "/records",
                    f"record file is not listed in the index: {candidate}",
                    severity,
                )
            )
    return findings


def _load_index_records(
    root: Path,
    entry: RegistryEntry,
    document: Any,
    *,
    strict: bool,
) -> tuple[list[RecordDocument], list[ModelFinding]]:
    rows = document.get("records", []) if isinstance(document, dict) else []
    if not isinstance(rows, list):
        return [], []
    ids = [_row_value(row, "id") for row in rows]
    duplicate_ids = {
        value for value, count in Counter(value for value in ids if isinstance(value, str)).items() if count > 1
    }
    records: list[RecordDocument] = []
    findings: list[ModelFinding] = []
    referenced: set[Path] = set()
    seen_duplicates: set[str] = set()
    for index, row in enumerate(rows):
        base = f"/records/{index}"
        row_id = _row_value(row, "id")
        if isinstance(row_id, str) and row_id in duplicate_ids:
            if row_id in seen_duplicates:
                findings.append(ModelFinding("reference.duplicate", f"{base}/id", f"duplicate ID `{row_id}`"))
            seen_duplicates.add(row_id)
            continue
        record_type = _row_value(row, "record_type")
        record_set = entry.record_sets.get(record_type) if isinstance(record_type, str) else None
        if record_set is None:
            findings.append(ModelFinding("reference.type", f"{base}/record_type", f"unknown record type `{record_type}`"))
            continue
        raw_path = _row_value(row, "document")
        if isinstance(raw_path, str) and not _unsafe_relative_path(raw_path):
            referenced.add((root / Path(raw_path)).absolute())
        path = _safe_record_path(root, record_set.path_prefix, raw_path)
        if path is None:
            findings.append(ModelFinding("reference.path", f"{base}/document", "record document must stay inside its registered path prefix"))
            continue
        resolved = path.resolve(strict=False)
        referenced.add(resolved)
        if not path.is_file():
            findings.append(ModelFinding("reference.document", f"{base}/document", f"record document is missing: {path}"))
            continue
        try:
            record = load_document(path)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/document"))
            continue
        try:
            schema = load_document(record_set.schema_path)
            schema_findings = validate_schema(record, schema)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/document"))
            continue
        if schema_findings:
            findings.extend(_prefix_schema_finding(finding, f"{base}/document") for finding in schema_findings)
            continue
        if not isinstance(record, dict):
            continue
        actual_id = record.get("id")
        actual_type = record.get("record_type")
        actual_revision = record.get("revision")
        mismatched = False
        for code, pointer, expected, actual in (
            ("index.id", "id", row_id, actual_id),
            ("index.type", "record_type", record_type, actual_type),
            ("index.revision", "expected_revision", _row_value(row, "expected_revision"), actual_revision),
        ):
            if expected != actual:
                findings.append(ModelFinding(code, f"{base}/{pointer}", f"index value {expected!r} does not match record value {actual!r}"))
                mismatched = True
        if not isinstance(actual_id, str) or re.fullmatch(record_set.id_pattern, actual_id) is None:
            findings.append(ModelFinding("index.id", f"{base}/id", f"record ID `{actual_id}` does not match the registered pattern"))
            mismatched = True
        try:
            digest = semantic_hash(record, excluded_paths=record_set.hash_excluded_paths)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/expected_hash"))
            continue
        if _row_value(row, "expected_hash") != digest:
            findings.append(ModelFinding("index.hash", f"{base}/expected_hash", "index hash does not match the canonical record hash"))
            mismatched = True
        if mismatched or not isinstance(actual_revision, int) or isinstance(actual_revision, bool):
            continue
        records.append(RecordDocument(entry.name, record_type, path, record, actual_id, actual_revision, digest, base))
    findings.extend(_orphan_findings(entry, referenced, strict=strict))
    return records, findings


def load_model_document(
    root: Path,
    entry: RegistryEntry,
    *,
    document_path: Path | None = None,
    strict: bool = False,
) -> ModelDocument:
    """Load one registry model without falling back when an index record is invalid."""
    path = document_path or entry.default_path
    document, schema_findings = _load_base(entry, path)
    if document is None or schema_findings or entry.document_kind != "index":
        return ModelDocument(entry, path, document, tuple(schema_findings))
    records, findings = _load_index_records(root.resolve(), entry, document, strict=strict)
    return ModelDocument(entry, path, document, (), tuple(records), tuple(findings))


def build_object_catalog(models: Iterable[ModelDocument]) -> ObjectCatalog:
    """Build a global catalog only from schema-clean record documents."""
    candidates: dict[str, list[CatalogObject]] = {}
    for model in models:
        for record in model.records:
            obj = CatalogObject(record.object_id, record.record_type, record.model_name, record.document, record.revision, record.object_hash, record.pointer)
            candidates.setdefault(record.object_id, []).append(obj)
        if not model.schema_clean or not isinstance(model.document, dict):
            continue
        virtual_specs = {
            "editorial": (
                ("story_candidates", "story"),
                ("argument_moves", "move"),
                ("visual_obligations", "visual"),
            ),
            "results_hierarchy": (("items", "results_item"),),
        }.get(model.entry.name, ())
        for field, object_type in virtual_specs:
            values = model.document.get(field, [])
            if not isinstance(values, list):
                continue
            for index, value in enumerate(values):
                if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                    continue
                object_id = value["id"]
                pointer = f"/{field}/{index}"
                obj = CatalogObject(
                    object_id,
                    object_type,
                    model.entry.name,
                    value,
                    None,
                    semantic_hash(value),
                    pointer,
                )
                candidates.setdefault(object_id, []).append(obj)
    objects: dict[str, CatalogObject] = {}
    findings: list[ModelFinding] = []
    for object_id, occurrences in candidates.items():
        if len(occurrences) > 1:
            findings.append(ModelFinding("reference.duplicate", occurrences[1].pointer + "/id", f"duplicate ID `{object_id}` across the object catalog"))
        else:
            objects[object_id] = occurrences[0]
    return ObjectCatalog(objects, tuple(findings))
