"""Validated authority inputs at the P3 compiler boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass, field
from collections.abc import Mapping
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any

import yaml

from paperops.model_state import (
    ModelAuthorityState,
    ModelStateError,
    read_model_states,
)
from paperops.model_migration.staging import StagingError, transaction_paths
from paperops.model_migration.transaction import TransactionError, plan_adoption
from paperops.model_validation import (
    ValidationResult,
    run_manuscript_compile_readiness,
    run_model_hash,
)

from .types import AuthoritySnapshot, CompileFinding, CompileRequest


_COMPILE_MODELS = (
    "research",
    "editorial",
    "results_hierarchy",
    "manuscript",
)
_AUTHORITY_TARGETS = {
    "research": ("_paperops/model/research",),
    "editorial": ("_paperops/model/editorial",),
    "results_hierarchy": ("_paperops/model/editorial",),
    "manuscript": ("_paperops/model/manuscript",),
}
_AUTHORITY_MODELS = {
    "research": ("research",),
    "editorial": ("editorial", "results_hierarchy"),
    "results_hierarchy": ("editorial", "results_hierarchy"),
    "manuscript": ("manuscript",),
}
_ROOT_DOCUMENTS = {
    "research": ("_paperops/model/research/index.yml", "index", ("/metadata/updated_at",)),
    "editorial": (
        "_paperops/model/editorial/editorial-model.yml",
        "aggregate",
        ("/metadata/updated_at",),
    ),
    "results_hierarchy": (
        "_paperops/model/editorial/results-hierarchy.yml",
        "aggregate",
        (),
    ),
    "manuscript": ("_paperops/model/manuscript/index.yml", "index", ("/metadata/updated_at",)),
}
_RECORD_PREFIXES = {
    "research": {
        "claim": "_paperops/model/research/claims/",
        "result": "_paperops/model/research/results/",
        "figure": "_paperops/model/research/figures/",
        "source": "_paperops/model/research/sources/",
        "scientific_gate": "_paperops/model/research/gates/",
    },
    "manuscript": {
        "section": "_paperops/model/manuscript/sections/",
        "block": "_paperops/model/manuscript/blocks/",
    },
}
_VIRTUAL_OBJECTS = {
    "editorial": (
        ("story_candidates", "story"),
        ("argument_moves", "move"),
        ("visual_obligations", "visual"),
    ),
    "results_hierarchy": (("items", "results_item"),),
}
_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_JOURNAL_KEYS = {
    "schema_version",
    "transaction_id",
    "action",
    "model_name",
    "models",
    "state",
    "targets",
    "state_hashes",
    "manifest_existed",
    "manifest_hash",
    "manifest_candidate_hash",
}


class CompileInputError(RuntimeError):
    """Reject a compile request before any untrusted model reaches the Writer."""

    def __init__(self, finding: CompileFinding) -> None:
        super().__init__(finding.message)
        self.finding = finding


@dataclass(frozen=True)
class LoadedCompileInputs:
    """Detached, validated input boundary consumed by the pure materializer."""

    source_mode: str
    applicable: bool
    authority: tuple[AuthoritySnapshot, ...]
    readiness: ValidationResult
    documents: tuple["LoadedModelDocument", ...] = ()
    objects: tuple["LoadedCatalogObject", ...] = ()


@dataclass(frozen=True)
class LoadedModelDocument:
    model_name: str
    identity: str
    document_type: str
    semantic_hash: str
    document: Mapping[str, object] = field(repr=False)


@dataclass(frozen=True)
class LoadedCatalogObject:
    object_id: str
    object_type: str
    model_name: str
    identity: str
    revision: int | None
    semantic_hash: str
    document: Mapping[str, object] = field(repr=False)


def _reject_source_mode(request: CompileRequest) -> None:
    has_transaction = bool(request.shadow_transaction_id)
    if (request.source_mode == "authoritative" and has_transaction) or (
        request.source_mode == "shadow" and not has_transaction
    ):
        raise CompileInputError(
            CompileFinding(
                code="compile.authority_source",
                pointer="/source_mode",
                message=(
                    "authoritative input must not name a shadow transaction, and "
                    "shadow input must name one"
                ),
            )
        )


def _input_error(code: str, pointer: str, message: str) -> CompileInputError:
    return CompileInputError(CompileFinding(code=code, pointer=pointer, message=message))


def _registered_identity(value: str) -> Path:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not value
        or "\x00" in value
        or "\\" in value
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or any(part in {"", ".", ".."} for part in posix.parts)
        or value != posix.as_posix()
    ):
        raise _input_error(
            "compile.input_path",
            "/document",
            "registered document must use a safe project-relative path",
        )
    return Path(*posix.parts)


def _read_registered_bytes(root: Path, identity: str) -> bytes:
    relative = _registered_identity(identity)
    project = root.expanduser().absolute()
    current = project
    try:
        root_metadata = project.lstat()
        if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
            raise OSError("unsafe project root")
        for index, part in enumerate(relative.parts):
            current = current / part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise OSError("symlink component")
            is_last = index == len(relative.parts) - 1
            if is_last and not stat.S_ISREG(metadata.st_mode):
                raise OSError("document is not a regular file")
            if not is_last and not stat.S_ISDIR(metadata.st_mode):
                raise OSError("parent component is not a directory")
        return current.read_bytes()
    except OSError as error:
        raise _input_error(
            "compile.input_path",
            f"/{identity}",
            "registered document is missing or has an unsafe file type",
        ) from error


def _read_registered_yaml(root: Path, identity: str) -> dict[str, Any]:
    """Read one registered YAML mapping without following any symlink."""
    raw = _read_registered_bytes(root, identity)
    try:
        payload = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise _input_error(
            "compile.input_document",
            f"/{identity}",
            "registered document is not valid YAML",
        ) from error
    if not isinstance(payload, dict):
        raise _input_error(
            "compile.input_document",
            f"/{identity}",
            "registered document must be a YAML mapping",
        )
    return payload


def _freeze_json(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("non-string JSON key")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    raise TypeError(f"unsupported YAML value: {type(value).__name__}")


def _frozen_mapping(value: dict[str, Any], identity: str) -> Mapping[str, object]:
    _reject_private_document_values(value, identity)
    try:
        frozen = _freeze_json(value)
    except (TypeError, ValueError) as error:
        raise _input_error(
            "compile.input_document",
            f"/{identity}",
            "registered document contains a non-JSON value",
        ) from error
    if not isinstance(frozen, Mapping):
        raise AssertionError("mapping input did not freeze as a mapping")
    return frozen


_PRIVATE_KEY_COMPONENT = re.compile(r"[^a-z0-9]+")
_CREDENTIAL_URL = re.compile(
    r"(?i)https?://[^\s/@:]+:[^\s/@]+@"
)
_EMBEDDED_POSIX_PATH = re.compile(
    r"(?<![A-Za-z0-9._:/-])/(?:[^\s/]+/)*[^\s,;:)\]}>\"']+"
)
_EMBEDDED_WINDOWS_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:[\\/]|\\\\[^\\/\s]+[\\/])[^\s,;:)\]}>\"']+"
)
_FILE_URI = re.compile(r"(?i)\bfile:(?://)?[^\s]+")
_PARENT_TRAVERSAL = re.compile(
    r"(?<![A-Za-z0-9._-])(?:\.\.[\\/])+(?:[^\s\\/]+[\\/]?)+"
)
_AUTHORIZATION_CREDENTIAL = re.compile(
    r"(?i)\b(?:authorization|proxy-authorization)\s*[:=]\s*"
    r"(?:bearer|basic)\s+\S+"
)
_BEARER_CREDENTIAL = re.compile(
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:token|api[_-]?key|password|passwd|secret|credential)\s*[:=]\s*\S+"
)


def _reject_private_document_values(value: object, identity: str) -> None:
    sensitive_keys = {
        "password",
        "passwd",
        "secret",
        "credential",
        "apikey",
        "token",
        "authorization",
    }

    def walk(item: object) -> bool:
        if isinstance(item, dict):
            for key, child in item.items():
                components = {
                    part
                    for part in _PRIVATE_KEY_COMPONENT.split(str(key).lower())
                    if part
                }
                if components.intersection(sensitive_keys) or walk(child):
                    return True
            return False
        if isinstance(item, list):
            return any(walk(child) for child in item)
        if not isinstance(item, str):
            return False
        stripped = item.strip()
        posix = PurePosixPath(stripped)
        windows = PureWindowsPath(stripped)
        return (
            bool(stripped)
            and (
                posix.is_absolute()
                or windows.is_absolute()
                or bool(windows.drive)
                or _EMBEDDED_POSIX_PATH.search(stripped) is not None
                or _EMBEDDED_WINDOWS_PATH.search(stripped) is not None
                or _FILE_URI.search(stripped) is not None
                or _PARENT_TRAVERSAL.search(stripped) is not None
                or _CREDENTIAL_URL.search(stripped) is not None
                or _AUTHORIZATION_CREDENTIAL.search(stripped) is not None
                or _BEARER_CREDENTIAL.search(stripped) is not None
                or _SECRET_ASSIGNMENT.search(stripped) is not None
            )
        )

    if walk(value):
        raise _input_error(
            "compile.input_privacy",
            f"/{identity}",
            "registered document contains private location or credential material",
        )


def _semantic_hash(value: dict[str, Any], excluded: tuple[str, ...] = ()) -> str:
    normalized = copy.deepcopy(value)
    for pointer in excluded:
        current: object = normalized
        tokens = pointer.lstrip("/").split("/")
        for token in tokens[:-1]:
            current = current.get(token) if isinstance(current, dict) else None
        if isinstance(current, dict):
            current.pop(tokens[-1], None)
    encoded = json.dumps(
        normalized,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _load_index_records(
    root: Path,
    model: str,
    index: dict[str, Any],
) -> tuple[tuple[LoadedModelDocument, ...], tuple[LoadedCatalogObject, ...]]:
    prefixes = _RECORD_PREFIXES.get(model)
    rows = index.get("records")
    if prefixes is None or not isinstance(rows, list):
        raise _input_error(
            "compile.input_document",
            f"/{model}/records",
            "validated model index has an invalid records array",
        )
    documents: list[LoadedModelDocument] = []
    objects: list[LoadedCatalogObject] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise _input_error(
                "compile.input_document",
                f"/{model}/records/{row_index}",
                "validated index record must be a mapping",
            )
        object_id = row.get("id")
        object_type = row.get("record_type")
        identity = row.get("document")
        revision = row.get("expected_revision")
        expected_hash = row.get("expected_hash")
        if (
            not isinstance(object_id, str)
            or object_id in seen_ids
            or not isinstance(object_type, str)
            or object_type not in prefixes
            or not isinstance(identity, str)
            or identity in seen_paths
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or not isinstance(expected_hash, str)
            or _HASH_PATTERN.fullmatch(expected_hash) is None
        ):
            raise _input_error(
                "compile.input_document",
                f"/{model}/records/{row_index}",
                "validated index record envelope is inconsistent",
            )
        relative = _registered_identity(identity)
        prefix = _registered_identity(prefixes[object_type].rstrip("/"))
        if relative.parts[: len(prefix.parts)] != prefix.parts or len(relative.parts) <= len(prefix.parts):
            raise _input_error(
                "compile.input_path",
                f"/{model}/records/{row_index}/document",
                "record document escapes its registered path prefix",
            )
        document = _read_registered_yaml(root, identity)
        actual_hash = _semantic_hash(
            document,
            ("/approvals", "/metadata/updated_at"),
        )
        if (
            document.get("id") != object_id
            or document.get("record_type") != object_type
            or document.get("revision") != revision
            or actual_hash != expected_hash
        ):
            raise _input_error(
                "compile.input_changed",
                f"/{identity}",
                "registered record changed after checker validation",
            )
        frozen = _frozen_mapping(document, identity)
        documents.append(
            LoadedModelDocument(model, identity, object_type, actual_hash, frozen)
        )
        objects.append(
            LoadedCatalogObject(
                object_id,
                object_type,
                model,
                identity,
                revision,
                actual_hash,
                frozen,
            )
        )
        seen_ids.add(object_id)
        seen_paths.add(identity)
    return (
        tuple(sorted(documents, key=lambda item: item.identity)),
        tuple(sorted(objects, key=lambda item: (item.object_id, item.identity))),
    )


def _load_model_inputs(
    root: Path,
    authority: tuple[AuthoritySnapshot, ...],
) -> tuple[tuple[LoadedModelDocument, ...], tuple[LoadedCatalogObject, ...]]:
    authority_by_model = {item.model_name: item for item in authority}
    documents: list[LoadedModelDocument] = []
    objects: list[LoadedCatalogObject] = []
    for model in _COMPILE_MODELS:
        identity, document_type, exclusions = _ROOT_DOCUMENTS[model]
        document = _read_registered_yaml(root, identity)
        digest = _semantic_hash(document, exclusions)
        if digest != authority_by_model[model].model_hash:
            raise _input_error(
                "compile.input_changed",
                f"/{identity}",
                "model document changed after authority validation",
            )
        frozen = _frozen_mapping(document, identity)
        documents.append(
            LoadedModelDocument(model, identity, document_type, digest, frozen)
        )
        if document_type == "index":
            record_documents, record_objects = _load_index_records(root, model, document)
            documents.extend(record_documents)
            objects.extend(record_objects)
        for field, object_type in _VIRTUAL_OBJECTS.get(model, ()):
            values = document.get(field)
            if not isinstance(values, list):
                raise _input_error(
                    "compile.input_document",
                    f"/{identity}#/{field}",
                    "validated aggregate object array is malformed",
                )
            for index, value in enumerate(values):
                if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                    raise _input_error(
                        "compile.input_document",
                        f"/{identity}#/{field}/{index}",
                        "validated aggregate object is malformed",
                    )
                object_identity = f"{identity}#/{field}/{index}"
                objects.append(
                    LoadedCatalogObject(
                        object_id=value["id"],
                        object_type=object_type,
                        model_name=model,
                        identity=object_identity,
                        revision=None,
                        semantic_hash=_semantic_hash(value),
                        document=_frozen_mapping(value, object_identity),
                    )
                )
    order = {name: index for index, name in enumerate(_COMPILE_MODELS)}
    return (
        tuple(documents),
        tuple(
            sorted(
                objects,
                key=lambda item: (order[item.model_name], item.object_id, item.identity),
            )
        ),
    )


def _compile_targets(
    request: CompileRequest,
    objects: tuple[LoadedCatalogObject, ...],
) -> tuple[str, ...]:
    selected = request.targets
    if (
        not selected
        or len(set(selected)) != len(selected)
        or tuple(selected) != tuple(request.write_scope.section_ids)
    ):
        raise _input_error(
            "compile.target",
            "/targets",
            "compile targets must be unique and exactly match write scope sections",
        )
    catalog = {item.object_id: item for item in objects}
    if any(
        target not in catalog or catalog[target].object_type != "section"
        for target in selected
    ):
        raise _input_error(
            "compile.target",
            "/targets",
            "compile target is not a registered Manuscript section",
        )
    return tuple(selected)


def _run_readiness(root: Path, targets: tuple[str, ...]) -> ValidationResult:
    return run_manuscript_compile_readiness(root, targets)


def _read_states(root: Path) -> dict[str, ModelAuthorityState]:
    try:
        _read_registered_bytes(root, ".pops/manifest.toml")
        states = read_model_states(root)
    except (CompileInputError, ModelStateError, OSError, ValueError) as error:
        raise _input_error(
            "compile.authority_state",
            "/authority",
            "model authority state is missing or invalid",
        ) from error
    return states


def _require_v2_authority(root: Path) -> dict[str, ModelAuthorityState]:
    states = _read_states(root)
    if any(states[name].mode != "v2-authoritative" for name in _COMPILE_MODELS):
        raise _input_error(
            "compile.authority_state",
            "/authority",
            "compile requires v2-authoritative Research, Editorial, Results, and Manuscript models",
        )
    return states


def _migration_error(root: Path, error: TransactionError) -> CompileInputError:
    finding = error.finding
    message = finding.message.replace(str(root.absolute()), ".")
    return CompileInputError(
        CompileFinding(
            code=finding.code,
            pointer=finding.pointer,
            message=message,
            severity=finding.severity,
        )
    )


def _read_committed_journal(
    root: Path,
    model: str,
    transaction_id: str,
    state_hashes: dict[str, str],
) -> None:
    try:
        payload = json.loads(
            _preflight_authority_journal(root, transaction_id).decode("utf-8")
        )
    except (
        StagingError,
        CompileInputError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        raise _input_error(
            "compile.authority_journal",
            f"/authority/{model}",
            "committed adoption journal is missing or malformed",
        ) from error
    expected_models = _AUTHORITY_MODELS[model]
    raw_targets = payload.get("targets") if isinstance(payload, dict) else None
    target_keys = {"relative_path", "old_exists", "old_hash", "candidate_hash"}
    targets_valid = isinstance(raw_targets, list) and all(
        isinstance(item, dict)
        and set(item) == target_keys
        and isinstance(item.get("relative_path"), str)
        and isinstance(item.get("old_exists"), bool)
        and isinstance(item.get("old_hash"), str)
        and isinstance(item.get("candidate_hash"), str)
        and _HASH_PATTERN.fullmatch(item["candidate_hash"]) is not None
        and (
            (item["old_exists"] and _HASH_PATTERN.fullmatch(item["old_hash"]) is not None)
            or (not item["old_exists"] and item["old_hash"] == "")
        )
        for item in raw_targets
    )
    target_paths = (
        tuple(
            item.get("relative_path")
            for item in raw_targets
            if isinstance(item, dict) and isinstance(item.get("relative_path"), str)
        )
        if isinstance(raw_targets, list)
        else ()
    )
    raw_hashes = payload.get("state_hashes") if isinstance(payload, dict) else None
    expected_state_hashes = {
        name: state_hashes[name]
        for name in expected_models
        if name in state_hashes
    }
    raw_models = payload.get("models") if isinstance(payload, dict) else None
    journal_models = (
        tuple(raw_models)
        if isinstance(raw_models, list)
        and all(isinstance(item, str) for item in raw_models)
        else None
    )
    hashes_valid = (
        isinstance(raw_hashes, dict)
        and all(
            isinstance(name, str)
            and isinstance(digest, str)
            and _HASH_PATTERN.fullmatch(digest) is not None
            for name, digest in raw_hashes.items()
        )
    )
    valid = (
        isinstance(payload, dict)
        and set(payload) == _JOURNAL_KEYS
        and type(payload.get("schema_version")) is int
        and payload["schema_version"] == 1
        and payload.get("transaction_id") == transaction_id
        and payload.get("action") == "adopt"
        and payload.get("state") == "committed"
        and payload.get("model_name") in expected_models
        and journal_models == expected_models
        and targets_valid
        and target_paths == _AUTHORITY_TARGETS[model]
        and hashes_valid
        and raw_hashes == expected_state_hashes
        and isinstance(payload.get("manifest_existed"), bool)
        and isinstance(payload.get("manifest_hash"), str)
        and isinstance(payload.get("manifest_candidate_hash"), str)
        and _HASH_PATTERN.fullmatch(payload["manifest_candidate_hash"]) is not None
        and (
            (
                payload["manifest_existed"]
                and _HASH_PATTERN.fullmatch(payload["manifest_hash"]) is not None
            )
            or (not payload["manifest_existed"] and payload["manifest_hash"] == "")
        )
    )
    if not valid:
        raise _input_error(
            "compile.authority_journal",
            f"/authority/{model}",
            "committed adoption journal does not cover the expected model authority",
        )


def _authoritative_snapshots(root: Path) -> tuple[AuthoritySnapshot, ...]:
    states = _require_v2_authority(root)
    snapshots = [
        _authoritative_snapshot(root, model, states) for model in _COMPILE_MODELS
    ]
    if snapshots[1].transaction_id != snapshots[2].transaction_id:
        raise _input_error(
            "compile.authority_state",
            "/authority/editorial",
            "Editorial and Results hierarchy must share one adoption transaction",
        )
    return tuple(snapshots)


def _preflight_authority_journal(root: Path, transaction_id: str) -> bytes:
    """Reject unsafe journal components before P2 opens the journal."""
    try:
        project = root.expanduser().absolute()
        paths = transaction_paths(project, transaction_id)
        identity = paths.journal_path.relative_to(project).as_posix()
        return _read_registered_bytes(project, identity)
    except (StagingError, CompileInputError, ValueError) as error:
        raise _input_error(
            "compile.authority_journal",
            "/authority/journal",
            "committed authority journal is missing or has an unsafe file type",
        ) from error


def _authoritative_snapshot(
    root: Path,
    model: str,
    states: dict[str, ModelAuthorityState],
) -> AuthoritySnapshot:
    state = states[model]
    if state.mode != "v2-authoritative":
        raise _input_error(
            "compile.authority_state",
            f"/authority/{model}",
            "model is not v2-authoritative",
        )
    _preflight_authority_journal(root, state.last_adopt_transaction)
    try:
        plan = plan_adoption(root, model)
    except TransactionError as error:
        raise _migration_error(root, error) from error
    except StagingError as error:
        raise _input_error(
            "compile.authority_state",
            f"/authority/{model}",
            "model adoption transaction is unsafe",
        ) from error
    if not plan.no_op or plan.transaction_id != state.last_adopt_transaction:
        raise _input_error(
            "compile.authority_state",
            f"/authority/{model}",
            "model does not resolve to a committed v2 adoption",
        )
    validation = run_model_hash(root, model)
    if not validation.ok:
        finding = validation.findings[0] if validation.findings else None
        raise CompileInputError(
            CompileFinding(
                code=finding.code if finding else "compile.authority_validation",
                pointer=finding.pointer if finding else f"/authority/{model}",
                message=(
                    finding.message
                    if finding
                    else "current model failed authority hash validation"
                ),
                severity=finding.severity if finding else "error",
            )
        )
    current_hash = validation.hashes.get(model, "")
    if (
        not current_hash
        or current_hash != state.current_hash
        or current_hash != plan.state_hashes.get(model)
    ):
        raise _input_error(
            "compile.authority_hash",
            f"/authority/{model}",
            "checker, manifest, and adoption journal hashes do not agree",
        )
    _read_committed_journal(
        root,
        model,
        plan.transaction_id,
        plan.state_hashes,
    )
    return AuthoritySnapshot(
        model_name=model,
        mode="v2-authoritative",
        model_hash=current_hash,
        transaction_id=plan.transaction_id,
    )


@dataclass(frozen=True)
class _ShadowCandidate:
    identity: str
    object_id: str
    semantic_hash: str
    content: bytes


@dataclass(frozen=True)
class _ShadowReport:
    model_name: str
    affected_models: tuple[str, ...]
    candidates: tuple[_ShadowCandidate, ...]


def _byte_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _shadow_failure(code: str, pointer: str, message: str) -> CompileInputError:
    return _input_error(code, pointer, message)


def _strict_shadow_report(root: Path, transaction_id: str) -> _ShadowReport:
    try:
        paths = transaction_paths(root, transaction_id)
        project = root.expanduser().absolute()
        report_identity = paths.report_json_path.relative_to(project).as_posix()
        payload = json.loads(
            _read_registered_bytes(project, report_identity).decode("utf-8")
        )
    except (StagingError, CompileInputError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise _shadow_failure(
            "compile.shadow_report",
            "/shadow_transaction_id",
            "shadow report is missing, unsafe, or malformed",
        ) from error
    report_keys = {
        "schema_version",
        "transaction_id",
        "model_name",
        "adapter_version",
        "inventory",
        "candidates",
        "findings",
    }
    if not isinstance(payload, dict) or set(payload) != report_keys:
        raise _shadow_failure(
            "compile.shadow_report",
            "/report",
            "shadow report envelope is unsupported",
        )
    model = payload.get("model_name")
    if (
        type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
        or payload.get("transaction_id") != transaction_id
        or type(payload.get("adapter_version")) is not int
        or payload["adapter_version"] != 1
        or model not in _COMPILE_MODELS
    ):
        raise _shadow_failure(
            "compile.shadow_report",
            "/report",
            "shadow report does not match the requested transaction",
        )
    affected = _AUTHORITY_MODELS[model]
    states = _read_states(root)
    if any(
        states[name].mode != "shadow-compare"
        or states[name].last_shadow_transaction != transaction_id
        for name in affected
    ) or any(
        states[name].mode != "v2-authoritative"
        for name in _COMPILE_MODELS
        if name not in affected
    ):
        raise _shadow_failure(
            "compile.authority_state",
            "/authority",
            "manifest authority state does not select this shadow transaction",
        )

    findings = payload.get("findings")
    finding_keys = {"code", "pointer", "message", "severity", "source_path"}
    if not isinstance(findings, list):
        raise _shadow_failure(
            "compile.shadow_report", "/findings", "shadow findings must be an array"
        )
    for index, item in enumerate(findings):
        if (
            not isinstance(item, dict)
            or set(item) != finding_keys
            or not all(
                isinstance(item.get(key), str)
                for key in finding_keys
            )
            or item["severity"] not in {"error", "warning", "info"}
            or (item["pointer"] and not item["pointer"].startswith("/"))
        ):
            raise _shadow_failure(
                "compile.shadow_report",
                f"/findings/{index}",
                "shadow finding is malformed",
            )
        if item["source_path"]:
            try:
                _registered_identity(item["source_path"])
            except CompileInputError as error:
                raise _shadow_failure(
                    "compile.shadow_report",
                    f"/findings/{index}/source_path",
                    "shadow finding source path is unsafe",
                ) from error
    if any(item["severity"] == "error" for item in findings):
        raise _shadow_failure(
            "compile.shadow_report",
            "/findings",
            "shadow report contains blocking findings",
        )

    inventory = payload.get("inventory")
    inventory_keys = {
        "family",
        "legacy_id",
        "source_path",
        "pointer",
        "source_hash",
        "disposition",
        "target_id",
        "reason",
        "followup_phase",
    }
    if not isinstance(inventory, list):
        raise _shadow_failure(
            "compile.shadow_report", "/inventory", "shadow inventory must be an array"
        )
    checked_sources: dict[str, str] = {}
    for index, item in enumerate(inventory):
        if (
            not isinstance(item, dict)
            or set(item) != inventory_keys
            or not all(isinstance(item.get(key), str) for key in inventory_keys)
            or _HASH_PATTERN.fullmatch(item["source_hash"]) is None
            or (item["pointer"] and not item["pointer"].startswith("/"))
        ):
            raise _shadow_failure(
                "compile.shadow_report",
                f"/inventory/{index}",
                "shadow inventory row is malformed",
            )
        source_identity = item["source_path"]
        try:
            _registered_identity(source_identity)
            source_content = _read_registered_bytes(root, source_identity)
        except CompileInputError as error:
            raise _shadow_failure(
                "compile.shadow_source",
                f"/inventory/{index}/source_path",
                "shadow source is missing or unsafe",
            ) from error
        source_hash = _byte_hash(source_content)
        previous_hash = checked_sources.setdefault(source_identity, source_hash)
        if previous_hash != source_hash or source_hash != item["source_hash"]:
            raise _shadow_failure(
                "compile.shadow_source",
                f"/inventory/{index}/source_hash",
                "shadow source changed after candidate generation",
            )

    candidates = payload.get("candidates")
    candidate_keys = {
        "relative_path",
        "object_id",
        "semantic_hash",
        "content_hash",
    }
    if not isinstance(candidates, list) or not candidates:
        raise _shadow_failure(
            "compile.shadow_report",
            "/candidates",
            "shadow report requires declared candidate documents",
        )
    candidate_root = paths.candidate_dir
    loaded_candidates: list[_ShadowCandidate] = []
    seen_paths: set[str] = set()
    seen_objects: set[str] = set()
    allowed_prefixes = tuple(_AUTHORITY_TARGETS[name][0] for name in affected)
    for index, item in enumerate(candidates):
        if (
            not isinstance(item, dict)
            or set(item) != candidate_keys
            or not all(isinstance(item.get(key), str) for key in candidate_keys)
            or _HASH_PATTERN.fullmatch(item["semantic_hash"]) is None
            or _HASH_PATTERN.fullmatch(item["content_hash"]) is None
        ):
            raise _shadow_failure(
                "compile.shadow_report",
                f"/candidates/{index}",
                "shadow candidate row is malformed",
            )
        identity = item["relative_path"]
        object_id = item["object_id"]
        try:
            relative = _registered_identity(identity)
        except CompileInputError as error:
            raise _shadow_failure(
                "compile.shadow_report",
                f"/candidates/{index}/relative_path",
                "shadow candidate path is unsafe",
            ) from error
        allowed = any(
            relative == _registered_identity(prefix)
            or relative.parts[: len(_registered_identity(prefix).parts)]
            == _registered_identity(prefix).parts
            for prefix in allowed_prefixes
        )
        if (
            not allowed
            or identity in seen_paths
            or object_id in seen_objects
            or not object_id
        ):
            raise _shadow_failure(
                "compile.shadow_report",
                f"/candidates/{index}",
                "shadow candidate is duplicate or outside the model target",
            )
        try:
            content = _read_registered_bytes(candidate_root, identity)
        except CompileInputError as error:
            raise _shadow_failure(
                "compile.shadow_candidate",
                f"/candidates/{index}/relative_path",
                "declared shadow candidate is missing or unsafe",
            ) from error
        if _byte_hash(content) != item["content_hash"]:
            raise _shadow_failure(
                "compile.shadow_candidate",
                f"/candidates/{index}/content_hash",
                "declared shadow candidate changed after validation",
            )
        root_model = next(
            (
                name
                for name in affected
                if identity == _ROOT_DOCUMENTS[name][0]
            ),
            None,
        )
        if root_model is not None:
            try:
                root_document = yaml.safe_load(content)
            except yaml.YAMLError as error:
                raise _shadow_failure(
                    "compile.shadow_report",
                    f"/candidates/{index}/object_id",
                    "shadow root candidate document is malformed",
                ) from error
            if root_model == "editorial":
                expected_object_id = (
                    root_document.get("model_id")
                    if isinstance(root_document, dict)
                    else None
                )
            else:
                expected_object_id = root_model
            if object_id != expected_object_id:
                raise _shadow_failure(
                    "compile.shadow_report",
                    f"/candidates/{index}/object_id",
                    "shadow root candidate uses a non-canonical object ID",
                )
        loaded_candidates.append(
            _ShadowCandidate(identity, object_id, item["semantic_hash"], content)
        )
        seen_paths.add(identity)
        seen_objects.add(object_id)
    expected_roots = {_ROOT_DOCUMENTS[name][0] for name in affected}
    if not expected_roots.issubset(seen_paths):
        raise _shadow_failure(
            "compile.shadow_report",
            "/candidates",
            "shadow report does not include every affected model root document",
        )
    if model in {"editorial", "results_hierarchy"} and seen_paths != expected_roots:
        raise _shadow_failure(
            "compile.shadow_report",
            "/candidates",
            "Editorial shadow must declare exactly its paired aggregate documents",
        )
    return _ShadowReport(model, affected, tuple(loaded_candidates))


def _copy_shadow_project(source: Path, destination: Path) -> None:
    """Copy only checker inputs, refusing every symlink and special file."""
    project = source.expanduser().absolute()
    try:
        project_metadata = project.lstat()
    except OSError as error:
        raise _shadow_failure(
            "compile.shadow_copy", "/", "shadow project root is missing or unsafe"
        ) from error
    if stat.S_ISLNK(project_metadata.st_mode) or not stat.S_ISDIR(
        project_metadata.st_mode
    ):
        raise _shadow_failure(
            "compile.shadow_copy", "/", "shadow project root is missing or unsafe"
        )

    def copy_entry(source_path: Path, target_path: Path, pointer: str) -> None:
        try:
            metadata = source_path.lstat()
        except OSError as error:
            raise _shadow_failure(
                "compile.shadow_copy",
                pointer,
                "required shadow checker input is missing",
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise _shadow_failure(
                "compile.shadow_copy",
                pointer,
                "shadow checker input contains a symlink",
            )
        if stat.S_ISDIR(metadata.st_mode):
            target_path.mkdir(parents=True, exist_ok=True)
            for child in sorted(source_path.iterdir(), key=lambda item: item.name):
                copy_entry(
                    child,
                    target_path / child.name,
                    f"{pointer.rstrip('/')}/{child.name}",
                )
            return
        if not stat.S_ISREG(metadata.st_mode):
            raise _shadow_failure(
                "compile.shadow_copy",
                pointer,
                "shadow checker input contains a special file",
            )
        try:
            content = source_path.read_bytes()
        except OSError as error:
            raise _shadow_failure(
                "compile.shadow_copy",
                pointer,
                "shadow checker input cannot be read",
            ) from error
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        target_path.chmod(stat.S_IMODE(metadata.st_mode))

    destination.mkdir(parents=True, exist_ok=False)
    for relative_text in (
        "scripts",
        "_paperops/defaults/schemas",
        "_paperops/model",
    ):
        relative = _registered_identity(relative_text)
        current = project
        for part in relative.parts:
            current = current / part
            try:
                metadata = current.lstat()
            except OSError as error:
                raise _shadow_failure(
                    "compile.shadow_copy",
                    f"/{relative_text}",
                    "required shadow checker tree is missing",
                ) from error
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise _shadow_failure(
                    "compile.shadow_copy",
                    f"/{relative_text}",
                    "shadow checker tree has an unsafe path component",
                )
        copy_entry(current, destination / relative, f"/{relative_text}")


def _candidate_owner(identity: str) -> str | None:
    for model in _COMPILE_MODELS:
        root_identity = _ROOT_DOCUMENTS[model][0]
        if identity == root_identity:
            return model
    relative = _registered_identity(identity)
    for model in ("research", "manuscript"):
        prefix = _registered_identity(_AUTHORITY_TARGETS[model][0])
        if relative.parts[: len(prefix.parts)] == prefix.parts:
            return model
    return None


def _shadow_inputs(
    root: Path,
    request: CompileRequest,
) -> LoadedCompileInputs:
    transaction_id = request.shadow_transaction_id
    report = _strict_shadow_report(root, transaction_id)
    states = _read_states(root)
    with tempfile.TemporaryDirectory(prefix="pops-compile-shadow-") as tmp:
        target = Path(tmp) / "project"
        _copy_shadow_project(root, target)
        for relative in dict.fromkeys(
            _AUTHORITY_TARGETS[name][0] for name in report.affected_models
        ):
            tracked = target / relative
            if tracked.is_symlink() or tracked.is_file():
                tracked.unlink()
            elif tracked.is_dir():
                shutil.rmtree(tracked)
        for candidate in report.candidates:
            destination = target / candidate.identity
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(candidate.content)

        shadow_hashes: dict[str, str] = {}
        for model in _COMPILE_MODELS:
            validation = run_model_hash(target, model)
            if not validation.ok:
                first = validation.findings[0] if validation.findings else None
                raise _shadow_failure(
                    "compile.shadow_validation",
                    first.pointer if first else f"/authority/{model}",
                    first.message if first else "shadow model validation failed",
                )
            shadow_hashes[model] = validation.hashes[model]
        candidate_hashes = {
            item.identity: item.semantic_hash for item in report.candidates
        }
        if any(
            shadow_hashes[name] != candidate_hashes.get(_ROOT_DOCUMENTS[name][0])
            for name in report.affected_models
        ):
            raise _shadow_failure(
                "compile.shadow_candidate",
                "/candidates",
                "shadow candidate semantic hash disagrees with the checker",
            )
        for candidate in report.candidates:
            owner = _candidate_owner(candidate.identity)
            if owner is None or owner not in report.affected_models:
                raise _shadow_failure(
                    "compile.shadow_candidate",
                    f"/{candidate.identity}",
                    "shadow candidate has no affected model owner",
                )
            if candidate.identity == _ROOT_DOCUMENTS[owner][0]:
                actual_hash = shadow_hashes[owner]
            else:
                validation = run_model_hash(target, owner, candidate.object_id)
                if not validation.ok:
                    raise _shadow_failure(
                        "compile.shadow_candidate",
                        f"/{candidate.identity}",
                        "shadow candidate object is absent from the validated catalog",
                    )
                actual_hash = validation.hashes.get(candidate.object_id, "")
            if actual_hash != candidate.semantic_hash:
                raise _shadow_failure(
                    "compile.shadow_candidate",
                    f"/{candidate.identity}",
                    "shadow candidate semantic hash disagrees with the object catalog",
                )

        authority: list[AuthoritySnapshot] = []
        for model in _COMPILE_MODELS:
            if model in report.affected_models:
                authority.append(
                    AuthoritySnapshot(
                        model_name=model,
                        mode="shadow",
                        model_hash=shadow_hashes[model],
                        transaction_id=transaction_id,
                    )
                )
            else:
                authority.append(_authoritative_snapshot(root, model, states))
        authority_tuple = tuple(authority)
        documents, objects = _load_model_inputs(target, authority_tuple)
        targets = _compile_targets(request, objects)
        readiness = _run_readiness(target, targets)
        return LoadedCompileInputs(
            source_mode="shadow",
            applicable=False,
            authority=authority_tuple,
            readiness=readiness,
            documents=documents,
            objects=objects,
        )


def load_compile_inputs(root: Path, request: CompileRequest) -> LoadedCompileInputs:
    """Return a detached snapshot only after its model authority is validated."""
    _reject_source_mode(request)
    if request.source_mode == "authoritative":
        authority = _authoritative_snapshots(root)
        documents, objects = _load_model_inputs(root, authority)
        targets = _compile_targets(request, objects)
        readiness = _run_readiness(root, targets)
        return LoadedCompileInputs(
            source_mode="authoritative",
            applicable=True,
            authority=authority,
            readiness=readiness,
            documents=documents,
            objects=objects,
        )
    return _shadow_inputs(root, request)


__all__ = [
    "CompileInputError",
    "LoadedCatalogObject",
    "LoadedCompileInputs",
    "LoadedModelDocument",
    "load_compile_inputs",
]
