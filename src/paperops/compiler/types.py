"""Immutable values shared by the P3 compiler and Writer boundary."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, Mapping


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SEMANTIC_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_SEVERITIES = frozenset({"error", "warning", "info"})
_SOURCE_MODES = frozenset({"authoritative", "shadow"})
_SCOPE_LEVELS = frozenset({"block", "section", "manuscript"})
_SNAPSHOT_KINDS = frozenset({"catalog", "content"})


def _validate_id(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must match ^[A-Za-z0-9][A-Za-z0-9._-]*$"
        )


def _validate_hash(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _SEMANTIC_HASH.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be sha256:<64 lowercase hex>")


def _validate_relative_identity(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ValueError(f"{field_name} must be a non-empty project-relative identity")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    parts = value.split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or bool(windows.root)
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ValueError(f"{field_name} must be a safe project-relative identity")


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence of strings")
    result = tuple(value)
    if not all(isinstance(item, str) for item in result):
        raise TypeError(f"{field_name} must contain only strings")
    return result


def _typed_tuple(value: object, expected: type[Any], field_name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence of {expected.__name__}")
    result = tuple(value)
    if not all(isinstance(item, expected) for item in result):
        raise TypeError(f"{field_name} must contain only {expected.__name__}")
    return result


def _freeze_json(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, Path):
        raise TypeError("path objects are not JSON values; use a relative identity")
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _freeze_json(to_dict())
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _json_compatible(value: object) -> Any:
    """Return detached JSON-compatible data for DTO output and canonical storage."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            result[key] = _json_compatible(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, Path):
        raise TypeError("path objects are not JSON values; use a relative identity")
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_compatible(to_dict())
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


@dataclass(frozen=True)
class CompileFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"
    identity: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("finding code must be a non-empty string")
        if not isinstance(self.pointer, str) or (
            self.pointer and not self.pointer.startswith("/")
        ):
            raise ValueError("finding pointer must be empty or a JSON Pointer")
        if not isinstance(self.message, str):
            raise TypeError("finding message must be a string")
        if self.severity not in _SEVERITIES:
            raise ValueError("finding severity must be error, warning, or info")
        if self.identity:
            _validate_relative_identity(self.identity, "finding identity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "pointer": self.pointer,
            "message": self.message,
            "severity": self.severity,
            "identity": self.identity,
        }


@dataclass(frozen=True)
class InputSnapshot:
    identity: str
    input_type: str
    semantic_hash: str
    relation: str
    model_name: str = ""
    revision: int | None = None
    snapshot_kind: str = "catalog"
    content_hash: str = ""

    def __post_init__(self) -> None:
        _validate_relative_identity(self.identity, "input identity")
        _validate_id(self.input_type, "input type")
        _validate_hash(self.semantic_hash, "input semantic hash")
        _validate_id(self.relation, "input relation")
        if self.model_name:
            _validate_id(self.model_name, "input model name")
        if self.revision is not None and (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ValueError("input revision must be a positive integer")
        if self.snapshot_kind not in _SNAPSHOT_KINDS:
            raise ValueError("snapshot kind must be catalog or content")
        if self.content_hash:
            _validate_hash(self.content_hash, "input content hash")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.snapshot_kind,
            "identity": self.identity,
            "type": self.input_type,
            "hash": self.semantic_hash,
            "relation": self.relation,
        }
        if self.model_name:
            result["model"] = self.model_name
        if self.revision is not None:
            result["revision"] = self.revision
        if self.content_hash:
            result["content_hash"] = self.content_hash
        return result


@dataclass(frozen=True)
class AuthoritySnapshot:
    model_name: str
    mode: str
    model_hash: str
    transaction_id: str = ""

    def __post_init__(self) -> None:
        _validate_id(self.model_name, "authority model name")
        _validate_id(self.mode, "authority mode")
        _validate_hash(self.model_hash, "authority model hash")
        if self.transaction_id:
            _validate_id(self.transaction_id, "authority transaction id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "mode": self.mode,
            "hash": self.model_hash,
            "transaction_id": self.transaction_id,
        }


@dataclass(frozen=True)
class WriteScope:
    level: str
    languages: tuple[str, ...]
    files: tuple[str, ...]
    section_ids: tuple[str, ...] = ()
    block_ids: tuple[str, ...] = ()
    allowed_operations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.level not in _SCOPE_LEVELS:
            raise ValueError("write scope level must be block, section, or manuscript")
        languages = _string_tuple(self.languages, "write scope languages")
        files = _string_tuple(self.files, "write scope files")
        section_ids = _string_tuple(self.section_ids, "write scope section IDs")
        block_ids = _string_tuple(self.block_ids, "write scope block IDs")
        operations = _string_tuple(
            self.allowed_operations, "write scope allowed operations"
        )
        for language in languages:
            _validate_id(language, "write scope language")
        for relative in files:
            _validate_relative_identity(relative, "write scope file")
        for section_id in section_ids:
            _validate_id(section_id, "write scope section ID")
        for block_id in block_ids:
            _validate_id(block_id, "write scope block ID")
        for operation in operations:
            _validate_id(operation, "write scope operation")
        object.__setattr__(self, "languages", languages)
        object.__setattr__(self, "files", files)
        object.__setattr__(self, "section_ids", section_ids)
        object.__setattr__(self, "block_ids", block_ids)
        object.__setattr__(self, "allowed_operations", operations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "languages": list(self.languages),
            "files": list(self.files),
            "section_ids": list(self.section_ids),
            "block_ids": list(self.block_ids),
            "allowed_operations": list(self.allowed_operations),
        }


@dataclass(frozen=True)
class CompileRequest:
    targets: tuple[str, ...]
    write_scope: WriteScope
    source_mode: str = "authoritative"
    shadow_transaction_id: str = ""

    def __post_init__(self) -> None:
        targets = _string_tuple(self.targets, "compile targets")
        for target in targets:
            _validate_id(target, "compile target")
        if not isinstance(self.write_scope, WriteScope):
            raise TypeError("compile write_scope must be a WriteScope")
        if self.source_mode not in _SOURCE_MODES:
            raise ValueError("compile source mode must be authoritative or shadow")
        if self.shadow_transaction_id:
            _validate_id(self.shadow_transaction_id, "shadow transaction id")
        object.__setattr__(self, "targets", targets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "targets": list(self.targets),
            "write_scope": self.write_scope.to_dict(),
            "source_mode": self.source_mode,
            "shadow_transaction_id": self.shadow_transaction_id,
        }


@dataclass(frozen=True)
class SectionPlan:
    section_id: str
    revision: int
    semantic_hash: str
    section_kind: str
    ordered_block_ids: tuple[str, ...]
    inputs: tuple[InputSnapshot, ...] = ()
    projection: Mapping[str, Any] = field(default_factory=dict)
    findings: tuple[CompileFinding, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        _validate_id(self.section_id, "section plan ID")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ValueError("section plan revision must be a positive integer")
        _validate_hash(self.semantic_hash, "section plan semantic hash")
        _validate_id(self.section_kind, "section plan kind")
        blocks = _string_tuple(self.ordered_block_ids, "section plan block IDs")
        for block_id in blocks:
            _validate_id(block_id, "section plan block ID")
        inputs = _typed_tuple(self.inputs, InputSnapshot, "section plan inputs")
        findings = _typed_tuple(
            self.findings, CompileFinding, "section plan findings"
        )
        if self.schema_version != 1:
            raise ValueError("unsupported section plan schema version")
        object.__setattr__(self, "ordered_block_ids", blocks)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "projection", _freeze_json(self.projection))
        object.__setattr__(self, "findings", findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "section_id": self.section_id,
            "revision": self.revision,
            "semantic_hash": self.semantic_hash,
            "section_kind": self.section_kind,
            "ordered_block_ids": list(self.ordered_block_ids),
            "inputs": [item.to_dict() for item in self.inputs],
            "projection": _json_compatible(self.projection),
            "findings": [item.to_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class WriterPacket:
    packet_id: str
    compile_id: str
    authority: tuple[AuthoritySnapshot, ...]
    write_scope: WriteScope
    inputs: tuple[InputSnapshot, ...]
    read_context: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    dependency_profile: Mapping[str, Any] = field(default_factory=dict)
    dependency_hash: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        _validate_id(self.packet_id, "Writer packet ID")
        _validate_id(self.compile_id, "compile ID")
        authority = _typed_tuple(
            self.authority, AuthoritySnapshot, "Writer packet authority"
        )
        inputs = _typed_tuple(self.inputs, InputSnapshot, "Writer packet inputs")
        if not isinstance(self.write_scope, WriteScope):
            raise TypeError("Writer packet write_scope must be a WriteScope")
        if self.schema_version != 1:
            raise ValueError("unsupported Writer packet schema version")
        if self.dependency_hash:
            _validate_hash(self.dependency_hash, "Writer packet dependency hash")
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "read_context", _freeze_json(self.read_context))
        object.__setattr__(self, "payload", _freeze_json(self.payload))
        object.__setattr__(
            self,
            "dependency_profile",
            _freeze_json(self.dependency_profile),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "packet_id": self.packet_id,
            "compile_id": self.compile_id,
            "authority": [item.to_dict() for item in self.authority],
            "write_scope": self.write_scope.to_dict(),
            "inputs": [item.to_dict() for item in self.inputs],
            "read_context": _json_compatible(self.read_context),
            "payload": _json_compatible(self.payload),
            "dependency_profile": _json_compatible(self.dependency_profile),
            "dependency_hash": self.dependency_hash,
        }


@dataclass(frozen=True)
class CompileBundle:
    compile_id: str
    source_mode: str
    request: CompileRequest
    authority: tuple[AuthoritySnapshot, ...]
    inputs: tuple[InputSnapshot, ...]
    section_plans: tuple[SectionPlan, ...]
    writer_packets: tuple[WriterPacket, ...]
    findings: tuple[CompileFinding, ...] = ()
    status: str = "ready"
    schema_version: int = 1
    compiler_contract_version: str = "p3-typed-compile-v1"
    applicable: bool = True
    contract_snapshot_hash: str = ""
    manuscript_snapshot_hash: str = ""
    global_context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_id(self.compile_id, "compile ID")
        if self.source_mode not in _SOURCE_MODES:
            raise ValueError("compile bundle source mode must be authoritative or shadow")
        if not isinstance(self.request, CompileRequest):
            raise TypeError("compile bundle request must be a CompileRequest")
        authority = _typed_tuple(
            self.authority, AuthoritySnapshot, "compile bundle authority"
        )
        inputs = _typed_tuple(self.inputs, InputSnapshot, "compile bundle inputs")
        plans = _typed_tuple(
            self.section_plans, SectionPlan, "compile bundle section plans"
        )
        packets = _typed_tuple(
            self.writer_packets, WriterPacket, "compile bundle Writer packets"
        )
        findings = _typed_tuple(
            self.findings, CompileFinding, "compile bundle findings"
        )
        _validate_id(self.status, "compile bundle status")
        _validate_id(
            self.compiler_contract_version,
            "compile bundle compiler contract version",
        )
        if type(self.applicable) is not bool:
            raise TypeError("compile bundle applicable must be boolean")
        if self.contract_snapshot_hash:
            _validate_hash(
                self.contract_snapshot_hash,
                "compile bundle contract snapshot hash",
            )
        if self.manuscript_snapshot_hash:
            _validate_hash(
                self.manuscript_snapshot_hash,
                "compile bundle manuscript snapshot hash",
            )
        if self.schema_version != 1:
            raise ValueError("unsupported compile bundle schema version")
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "section_plans", plans)
        object.__setattr__(self, "writer_packets", packets)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "global_context", _freeze_json(self.global_context))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "compiler_contract_version": self.compiler_contract_version,
            "compile_id": self.compile_id,
            "source_mode": self.source_mode,
            "status": self.status,
            "applicable": self.applicable,
            "contract_snapshot_hash": self.contract_snapshot_hash,
            "manuscript_snapshot_hash": self.manuscript_snapshot_hash,
            "request": self.request.to_dict(),
            "authority": [item.to_dict() for item in self.authority],
            "inputs": [item.to_dict() for item in self.inputs],
            "section_plans": [item.to_dict() for item in self.section_plans],
            "writer_packets": [item.to_dict() for item in self.writer_packets],
            "global_context": _json_compatible(self.global_context),
            "findings": [item.to_dict() for item in self.findings],
        }


def _relative_paths(paths: tuple[Path, ...], state_dir: Path) -> list[str]:
    project_root = state_dir.parents[2]
    return [path.relative_to(project_root).as_posix() for path in paths]


def _validate_state_directory(
    directory: object,
    identifier: str,
    state_name: str,
    field_name: str,
) -> Path:
    if not isinstance(directory, Path):
        raise TypeError(f"{field_name} must be a Path")
    if (
        not directory.is_absolute()
        or ".." in directory.parts
        or directory.name != identifier
        or directory.parent.name != state_name
        or directory.parent.parent.name != ".paperops"
    ):
        raise ValueError(
            f"{field_name} must be below .paperops/{state_name}/{identifier}"
        )
    return directory


def _require_exact_path(
    actual: object,
    expected: Path,
    field_name: str,
) -> None:
    if not isinstance(actual, Path):
        raise TypeError(f"{field_name} must be a Path")
    if actual != expected:
        raise ValueError(f"{field_name} must be {expected.name} below generated state")


@dataclass(frozen=True)
class CompilePaths:
    compile_id: str
    compile_dir: Path
    bundle_path: Path
    report_path: Path
    context_dir: Path
    global_context_path: Path
    plans_dir: Path
    packets_dir: Path

    def __post_init__(self) -> None:
        _validate_id(self.compile_id, "compile ID")
        directory = _validate_state_directory(
            self.compile_dir,
            self.compile_id,
            "compile",
            "compile directory",
        )
        _require_exact_path(
            self.bundle_path, directory / "bundle.json", "compile bundle path"
        )
        _require_exact_path(
            self.report_path, directory / "report.json", "compile report path"
        )
        _require_exact_path(
            self.context_dir, directory / "context", "compile context directory"
        )
        _require_exact_path(
            self.global_context_path,
            directory / "context" / "global.json",
            "compile global context path",
        )
        _require_exact_path(
            self.plans_dir, directory / "plans", "compile plans directory"
        )
        _require_exact_path(
            self.packets_dir, directory / "packets", "compile packets directory"
        )

    def to_dict(self) -> dict[str, Any]:
        names = _relative_paths(
            (
                self.compile_dir,
                self.bundle_path,
                self.report_path,
                self.context_dir,
                self.global_context_path,
                self.plans_dir,
                self.packets_dir,
            ),
            self.compile_dir,
        )
        return {
            "compile_id": self.compile_id,
            "compile_dir": names[0],
            "bundle_path": names[1],
            "report_path": names[2],
            "context_dir": names[3],
            "global_context_path": names[4],
            "plans_dir": names[5],
            "packets_dir": names[6],
        }


@dataclass(frozen=True)
class WriterPaths:
    session_id: str
    writer_dir: Path
    workspace_dir: Path
    base_manifest_path: Path
    patch_path: Path
    report_path: Path
    journal_path: Path

    def __post_init__(self) -> None:
        _validate_id(self.session_id, "Writer session ID")
        directory = _validate_state_directory(
            self.writer_dir,
            self.session_id,
            "writer",
            "Writer directory",
        )
        _require_exact_path(
            self.workspace_dir, directory / "workspace", "Writer workspace directory"
        )
        _require_exact_path(
            self.base_manifest_path,
            directory / "base-manifest.json",
            "Writer base manifest path",
        )
        _require_exact_path(
            self.patch_path, directory / "patch.json", "Writer patch path"
        )
        _require_exact_path(
            self.report_path, directory / "report.json", "Writer report path"
        )
        _require_exact_path(
            self.journal_path, directory / "journal.json", "Writer journal path"
        )

    def to_dict(self) -> dict[str, Any]:
        names = _relative_paths(
            (
                self.writer_dir,
                self.workspace_dir,
                self.base_manifest_path,
                self.patch_path,
                self.report_path,
                self.journal_path,
            ),
            self.writer_dir,
        )
        return {
            "session_id": self.session_id,
            "writer_dir": names[0],
            "workspace_dir": names[1],
            "base_manifest_path": names[2],
            "patch_path": names[3],
            "report_path": names[4],
            "journal_path": names[5],
        }


__all__ = [
    "AuthoritySnapshot",
    "CompileBundle",
    "CompileFinding",
    "CompilePaths",
    "CompileRequest",
    "InputSnapshot",
    "SectionPlan",
    "WriteScope",
    "WriterPacket",
    "WriterPaths",
]
