"""Load PaperOps aggregate/index models and build a schema-clean object catalog."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit

from paperops_schema import (
    ModelFinding,
    RegistryEntry,
    load_document,
    semantic_hash,
    validate_document_version,
    validate_extension_keys,
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
        return (
            self.document is not None
            and not self.schema_findings
            and not any(
                finding.code.startswith(("schema.", "document.", "registry."))
                for finding in self.catalog_findings
            )
        )

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


def _research_finding(code: str, obj: CatalogObject, suffix: str, message: str) -> ModelFinding:
    return ModelFinding(code, f"{obj.pointer}{suffix}", message)


def validate_research_semantics(catalog: ObjectCatalog) -> list[ModelFinding]:
    """Validate Research gate readiness, approvals, quantities, and provenance."""
    findings: list[ModelFinding] = []
    research = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "research"
    }
    quantity_ids: dict[str, tuple[CatalogObject, int]] = {}
    for obj in research.values():
        document = obj.document
        extensions = document.get("extensions")
        if isinstance(extensions, dict):
            for extension_finding in validate_extension_keys(extensions):
                findings.append(
                    _research_finding(
                        extension_finding.code,
                        obj,
                        f"/extensions{extension_finding.pointer}",
                        extension_finding.message,
                    )
                )
            for key in extensions:
                if isinstance(key, str) and _sensitive_extension_key(key):
                    findings.append(
                        _research_finding(
                            "semantic.extension",
                            obj,
                            f"/extensions/{key.replace('~', '~0').replace('/', '~1')}",
                            f"extension key `{key}` may not store credential or local-path state",
                        )
                    )
        if obj.object_type == "result":
            quantities = document.get("quantity_contracts", [])
            if isinstance(quantities, list):
                for index, quantity in enumerate(quantities):
                    quantity_id = quantity.get("id") if isinstance(quantity, dict) else None
                    if not isinstance(quantity_id, str):
                        continue
                    previous = quantity_ids.get(quantity_id)
                    if previous is not None:
                        findings.append(
                            _research_finding(
                                "reference.duplicate",
                                obj,
                                f"/quantity_contracts/{index}/id",
                                f"duplicate ID `{quantity_id}`",
                            )
                        )
                    else:
                        quantity_ids[quantity_id] = (obj, index)
            provenance = document.get("artifact_provenance_ids", [])
            _validate_public_provenance(obj, provenance, "/artifact_provenance_ids", findings)
        elif obj.object_type == "source":
            provenance = document.get("public_provenance_refs", [])
            _validate_public_provenance(obj, provenance, "/public_provenance_refs", findings)

    for claim in (obj for obj in research.values() if obj.object_type == "claim"):
        gate_id = claim.document.get("gate_id")
        paired_gate = research.get(gate_id) if isinstance(gate_id, str) else None
        if paired_gate is None or paired_gate.object_type != "scientific_gate":
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    claim,
                    "/gate_id",
                    f"claim gate `{gate_id}` is not a Research scientific gate",
                )
            )

    for gate in (obj for obj in research.values() if obj.object_type == "scientific_gate"):
        claim_id = gate.document.get("claim_id")
        claim = research.get(claim_id) if isinstance(claim_id, str) else None
        if claim is None or claim.object_type != "claim":
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    gate,
                    "/claim_id",
                    f"gate claim `{claim_id}` is not a Research claim",
                )
            )
            continue
        if (
            claim.document.get("gate_id") != gate.object_id
            or claim.document.get("gate_status") != gate.document.get("gate_decision")
        ):
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    gate,
                    "/claim_id",
                    f"gate `{gate.object_id}` and claim `{claim.object_id}` do not agree",
                )
            )
        if gate.document.get("gate_decision") != "ready_to_write":
            continue
        if claim.document.get("status") != "approved":
            findings.append(
                _research_finding(
                    "semantic.claim_not_writable",
                    gate,
                    "/gate_decision",
                    f"claim `{claim.object_id}` is not approved",
                )
            )
        approval_state = _scientific_approval_state(claim)
        if approval_state == "missing":
            findings.append(
                _research_finding(
                    "approval.missing",
                    claim,
                    "/approvals",
                    "current scientific_scope approval is required",
                )
            )
        elif approval_state == "stale":
            findings.append(
                _research_finding(
                    "approval.stale",
                    claim,
                    "/approvals",
                    "scientific_scope approval does not match current revision/hash",
                )
            )
        elif approval_state == "rejected":
            findings.append(
                _research_finding(
                    "approval.missing",
                    claim,
                    "/approvals",
                    "latest current scientific_scope decision is not approved",
                )
            )
    return findings


def _manuscript_finding(
    code: str,
    obj: CatalogObject,
    suffix: str,
    message: str,
) -> ModelFinding:
    return ModelFinding(code, f"{obj.pointer}{suffix}", message)


def _scientific_approval_state(claim: CatalogObject) -> str:
    approvals = claim.document.get("approvals", [])
    history = [
        approval
        for approval in approvals
        if isinstance(approval, dict)
        and approval.get("kind") == "scientific_scope"
    ] if isinstance(approvals, list) else []
    current = [
        approval
        for approval in history
        if approval.get("object_revision") == claim.revision
        and approval.get("object_hash") == claim.object_hash
    ]
    if not history:
        return "missing"
    if not current:
        return "stale"
    if current[-1].get("decision") != "approved":
        return "rejected"
    return "approved"


def validate_manuscript_semantics(catalog: ObjectCatalog) -> list[ModelFinding]:
    """Validate Manuscript structure and its Research write-readiness boundary."""
    findings: list[ModelFinding] = []
    manuscript = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "manuscript"
    }
    sections = {
        object_id: obj
        for object_id, obj in manuscript.items()
        if obj.object_type == "section"
    }
    blocks = {
        object_id: obj
        for object_id, obj in manuscript.items()
        if obj.object_type == "block"
    }
    research = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "research"
    }

    for obj in manuscript.values():
        extensions = obj.document.get("extensions")
        if isinstance(extensions, dict):
            for finding in validate_extension_keys(extensions):
                findings.append(
                    _manuscript_finding(
                        finding.code,
                        obj,
                        f"/extensions{finding.pointer}",
                        finding.message,
                    )
                )
        requires_compiled_state = obj.document.get("status") in {
            "compiled", "drafted", "verified", "stale", "removed",
        }
        if (
            requires_compiled_state
            and obj.object_type == "section"
            and not obj.document.get("compiled_manifest_ref")
        ):
            findings.append(
                _manuscript_finding(
                    "semantic.compiled_from",
                    obj,
                    "/compiled_manifest_ref",
                    "compiled section state requires a compiled manifest reference",
                )
            )
        dependency_hash = obj.document.get("dependency_hash")
        verified_hash = obj.document.get("last_verified_dependency_hash")
        if requires_compiled_state and not dependency_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.missing",
                    obj,
                    "/dependency_hash",
                    "compiled state requires a current dependency hash",
                )
            )
        if requires_compiled_state and not verified_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.missing",
                    obj,
                    "/last_verified_dependency_hash",
                    "compiled state requires a last verified dependency hash",
                )
            )
        if dependency_hash and verified_hash and dependency_hash != verified_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.stale",
                    obj,
                    "/last_verified_dependency_hash",
                    "verified dependency hash does not match the current dependency hash",
                )
            )

    for section in sections.values():
        ordered_ids = section.document.get("ordered_block_ids", [])
        if not isinstance(ordered_ids, list):
            continue
        if len(set(ordered_ids)) != len(ordered_ids):
            findings.append(
                _manuscript_finding(
                    "semantic.block_order",
                    section,
                    "/ordered_block_ids",
                    "ordered block IDs must be unique",
                )
            )
        for expected_position, block_id in enumerate(ordered_ids, start=1):
            block = blocks.get(block_id) if isinstance(block_id, str) else None
            if block is None or block.document.get("section_id") != section.object_id:
                findings.append(
                    _manuscript_finding(
                        "semantic.section_membership",
                        section,
                        f"/ordered_block_ids/{expected_position - 1}",
                        f"block `{block_id}` is not a member of section `{section.object_id}`",
                    )
                )
                continue
            if block.document.get("position") != expected_position:
                findings.append(
                    _manuscript_finding(
                        "semantic.block_order",
                        block,
                        "/position",
                        f"block position must be {expected_position} in its section",
                    )
                )

    for block in blocks.values():
        section_id = block.document.get("section_id")
        section = sections.get(section_id) if isinstance(section_id, str) else None
        ordered_ids = section.document.get("ordered_block_ids", []) if section else []
        if section is None or block.object_id not in ordered_ids:
            findings.append(
                _manuscript_finding(
                    "semantic.section_membership",
                    block,
                    "/section_id",
                    f"block `{block.object_id}` is not listed by its section `{section_id}`",
                )
            )

        allowed_operations = block.document.get("allowed_operations", [])
        if block.document.get("operation") not in allowed_operations:
            findings.append(
                _manuscript_finding(
                    "semantic.operation",
                    block,
                    "/operation",
                    "block operation must be included in allowed_operations",
                )
            )

        compiled_from = block.document.get("compiled_from")
        requires_compilation = block.document.get("status") in {
            "compiled", "drafted", "verified", "stale", "removed",
        }
        if compiled_from is None and not requires_compilation:
            continue
        complete_compilation = (
            isinstance(compiled_from, dict)
            and isinstance(compiled_from.get("compiler_version"), str)
            and bool(compiled_from.get("compiler_version"))
            and isinstance(compiled_from.get("schema_versions"), dict)
            and bool(compiled_from.get("schema_versions"))
            and isinstance(compiled_from.get("input_ids"), list)
            and bool(compiled_from.get("input_ids"))
            and isinstance(compiled_from.get("input_hashes"), list)
            and len(compiled_from.get("input_ids"))
            == len(compiled_from.get("input_hashes"))
        )
        if not complete_compilation:
            findings.append(
                _manuscript_finding(
                    "semantic.compiled_from",
                    block,
                    "/compiled_from",
                    "compiled blocks require complete compiler, schema, input ID, and input hash provenance",
                )
            )

        for index, claim_id in enumerate(block.document.get("claim_refs", [])):
            claim = research.get(claim_id) if isinstance(claim_id, str) else None
            if claim is None or claim.object_type != "claim":
                findings.append(
                    _manuscript_finding(
                        "reference.dangling",
                        block,
                        f"/claim_refs/{index}",
                        f"Research claim `{claim_id}` is not present",
                    )
                )
                continue
            approval_state = _scientific_approval_state(claim)
            if approval_state != "approved":
                code = "approval.stale" if approval_state == "stale" else "approval.missing"
                findings.append(
                    _manuscript_finding(
                        code,
                        block,
                        f"/claim_refs/{index}",
                        f"claim `{claim_id}` lacks a current approved scientific_scope decision",
                    )
                )
            gate_id = claim.document.get("gate_id")
            gate = research.get(gate_id) if isinstance(gate_id, str) else None
            if (
                claim.document.get("status") != "approved"
                or claim.document.get("gate_status") != "ready_to_write"
                or gate is None
                or gate.object_type != "scientific_gate"
                or gate.document.get("claim_id") != claim.object_id
                or gate.document.get("gate_decision") != "ready_to_write"
            ):
                findings.append(
                    _manuscript_finding(
                        "semantic.claim_not_writable",
                        block,
                        f"/claim_refs/{index}",
                        f"claim `{claim_id}` has not passed its ready_to_write gate",
                    )
                )

        reference_fields = {
            "result_refs": "result",
            "source_refs": "source",
            "figure_refs": "figure",
        }
        for field, expected_type in reference_fields.items():
            for index, object_id in enumerate(block.document.get(field, [])):
                target = research.get(object_id) if isinstance(object_id, str) else None
                if target is None or target.object_type != expected_type:
                    findings.append(
                        _manuscript_finding(
                            "reference.dangling",
                            block,
                            f"/{field}/{index}",
                            f"Research {expected_type} `{object_id}` is not present",
                        )
                    )
    return findings


def _validate_public_provenance(
    obj: CatalogObject,
    values: Any,
    suffix: str,
    findings: list[ModelFinding],
) -> None:
    if not isinstance(values, list):
        return
    for index, value in enumerate(values):
        if not isinstance(value, str) or not _valid_public_provenance(value):
            findings.append(
                _research_finding(
                    "semantic.public_provenance",
                    obj,
                    f"{suffix}/{index}",
                    "provenance must use a public or opaque identifier, not a local/raw path",
                )
            )


def _sensitive_extension_key(key: str) -> bool:
    components = [
        component
        for component in re.split(r"[-._]", key.casefold())
        if component
    ]
    if any(
        component in {"password", "passwd", "secret", "credential", "apikey"}
        for component in components
    ):
        return True
    sensitive_pairs = {
        ("api", "key"),
        ("access", "token"),
        ("auth", "token"),
        ("local", "path"),
        ("private", "key"),
        ("bearer", "token"),
        ("refresh", "token"),
        ("session", "token"),
        ("id", "token"),
    }
    return any(pair in sensitive_pairs for pair in zip(components, components[1:]))


def _valid_public_provenance(value: str) -> bool:
    if any(ord(character) < 32 or character.isspace() for character in value):
        return False
    if value.startswith("artifact:"):
        return re.fullmatch(r"artifact:[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None
    if value.startswith("commit:"):
        return re.fullmatch(r"commit:[0-9a-fA-F]{7,64}", value) is not None
    if value.startswith("doi:"):
        return (
            re.fullmatch(
                r"doi:10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+",
                value,
            )
            is not None
        )
    if value.startswith("url:"):
        if "\\" in value:
            return False
        try:
            parsed = urlsplit(value[4:])
        except ValueError:
            return False
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or bool(parsed.fragment)
        ):
            return False
        hostname = parsed.hostname.casefold().rstrip(".")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            ipv4_like_labels = hostname.split(".")
            if (
                (
                    1 < len(ipv4_like_labels) <= 4
                    and all(
                        re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", label)
                        is not None
                        for label in ipv4_like_labels
                    )
                )
                or "." not in hostname
                or hostname == "localhost"
                or hostname.endswith(
                    (
                        ".localhost", ".local", ".internal", ".lan",
                        ".localdomain", ".home.arpa",
                    )
                )
                or hostname in {"localdomain", "home.arpa"}
            ):
                return False
        else:
            if not address.is_global:
                return False
        sensitive_query_keys = {
            "token", "key", "password", "passwd", "secret", "credential",
            "api_key", "apikey", "access_token", "auth",
        }
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
            normalized = key.casefold().replace("-", "_")
            components = set(re.split(r"[._]", normalized))
            if normalized in sensitive_query_keys or components.intersection(
                {"token", "key", "password", "passwd", "secret", "credential", "auth"}
            ):
                return False
        return True
    return False


def _exception_finding(error: Exception, pointer: str) -> ModelFinding:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    if separator and "." in prefix and " " not in prefix:
        detail = detail.strip()
        if detail.startswith("/") and ":" in detail:
            error_pointer, _, error_detail = detail.partition(":")
            if pointer != "/":
                error_pointer = pointer + (
                    "" if error_pointer == "/" else error_pointer
                )
            return ModelFinding(prefix, error_pointer, error_detail.strip())
        return ModelFinding(prefix, pointer, detail)
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
                elif candidate.suffix.lower() in {".json", ".yml", ".yaml"}:
                    findings.append(
                        ModelFinding(
                            "reference.orphan",
                            "/records",
                            f"record file is not listed in the index: {candidate}",
                            severity,
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
        envelope_findings: list[ModelFinding] = []
        actual_id: Any = None
        actual_type: Any = None
        actual_revision: Any = None
        if isinstance(record, dict):
            actual_id = record.get("id")
            actual_type = record.get("record_type")
            actual_revision = record.get("revision")
            for code, pointer, expected, actual in (
                ("index.id", "id", row_id, actual_id),
                ("index.type", "record_type", record_type, actual_type),
                (
                    "index.revision",
                    "expected_revision",
                    _row_value(row, "expected_revision"),
                    actual_revision,
                ),
            ):
                if expected != actual:
                    envelope_findings.append(
                        ModelFinding(
                            code,
                            f"{base}/{pointer}",
                            f"index value {expected!r} does not match record value {actual!r}",
                        )
                    )
            if (
                not isinstance(actual_id, str)
                or re.fullmatch(record_set.id_pattern, actual_id) is None
            ):
                envelope_findings.append(
                    ModelFinding(
                        "index.id",
                        f"{base}/id",
                        f"record ID `{actual_id}` does not match the registered pattern",
                    )
                )
        findings.extend(envelope_findings)
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
        mismatched = bool(envelope_findings)
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
    actual_model_name = (
        document.get("model_name") if isinstance(document, dict) else None
    )
    if actual_model_name != entry.name:
        return ModelDocument(
            entry,
            path,
            document,
            (),
            catalog_findings=(
                ModelFinding(
                    "index.model_name",
                    "/model_name",
                    f"index model_name {actual_model_name!r} does not match "
                    f"registry model {entry.name!r}",
                ),
            ),
        )
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
            findings.append(
                ModelFinding(
                    "reference.duplicate",
                    occurrences[1].pointer + "/id",
                    f"duplicate ID `{object_id}`",
                )
            )
        else:
            objects[object_id] = occurrences[0]
    return ObjectCatalog(objects, tuple(findings))
