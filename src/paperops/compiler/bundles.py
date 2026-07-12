"""Atomic persistence and strict loading for deterministic P3 compile bundles."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import resolve_section_contract
from .inputs import CompileInputError, load_compile_inputs
from .materialize import (
    CompileContractSnapshot,
    compute_compile_id,
    materialize_compile,
)
from .storage import canonical_json_bytes, compile_paths, semantic_hash
from .tex import scan_manuscript
from .types import (
    AuthoritySnapshot,
    CompileBundle,
    CompileFinding,
    CompileRequest,
    InputSnapshot,
    SectionPlan,
    WriteScope,
    WriterPacket,
    _freeze_json,
    _json_compatible,
)


class BundleVerificationError(ValueError):
    """A persisted compile directory does not satisfy its closed manifest."""


def _hash_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _artifact(path: str, kind: str, content: bytes) -> dict[str, object]:
    return {"path": path, "kind": kind, "content_hash": _hash_bytes(content)}


@dataclass(frozen=True)
class VerifiedBundle:
    compile_id: str
    bundle: Mapping[str, Any]
    report: Mapping[str, Any]
    artifacts: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle", _freeze_json(self.bundle))
        object.__setattr__(self, "report", _freeze_json(self.report))
        object.__setattr__(
            self,
            "artifacts",
            tuple(_freeze_json(item) for item in self.artifacts),
        )


@dataclass(frozen=True)
class CompileResult:
    compile_id: str
    status: str
    applicable: bool
    findings: tuple[CompileFinding, ...] = ()
    artifacts: tuple[Mapping[str, Any], ...] = ()
    reused: bool = False
    refreshed: bool = False
    diagnostic_path: str = ""
    schema_version: int = 1

    @property
    def ok(self) -> bool:
        return self.status == "ready" and not any(
            item.severity == "error" for item in self.findings
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "compile_id": self.compile_id,
            "status": self.status,
            "applicable": self.applicable,
            "reused": self.reused,
            "refreshed": self.refreshed,
            "diagnostic_path": self.diagnostic_path,
            "artifacts": [_json_compatible(item) for item in self.artifacts],
            "findings": [item.to_dict() for item in self.findings],
        }


@dataclass(frozen=True)
class CompileCacheStatus:
    target: str
    results: tuple[CompileResult, ...]
    findings: tuple[CompileFinding, ...] = ()

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)


def _read_json_regular(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise BundleVerificationError("compile artifact is missing") from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise BundleVerificationError("compile artifact must be a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            raw = stream.read()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleVerificationError("compile artifact is not canonical JSON") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise BundleVerificationError("compile artifact is not canonical JSON")
    return value, raw


def _safe_artifact_rows(value: object) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        raise BundleVerificationError("compile artifact manifest must be an array")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "kind", "content_hash"}:
            raise BundleVerificationError("compile artifact manifest row is invalid")
        path = item.get("path")
        kind = item.get("kind")
        content_hash = item.get("content_hash")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or path in seen
            or not isinstance(kind, str)
            or not kind
            or not isinstance(content_hash, str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", content_hash) is None
        ):
            raise BundleVerificationError("compile artifact manifest row is invalid")
        seen.add(path)
        rows.append({"path": path, "kind": kind, "content_hash": content_hash})
    if [row["path"] for row in rows] != sorted(row["path"] for row in rows):
        raise BundleVerificationError("compile artifact manifest order is invalid")
    for row in rows:
        path = row["path"]
        expected_kind = (
            "global-context"
            if path == "context/global.json"
            else "report"
            if path == "report.json"
            else "section-plan"
            if path.startswith("plans/") and path.endswith(".json")
            else "writer-packet"
            if path.startswith("packets/") and path.endswith(".json")
            else ""
        )
        if row["kind"] != expected_kind:
            raise BundleVerificationError("compile artifact kind is invalid")
    return tuple(rows)


def _exact(value: object, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise BundleVerificationError(f"{name} shape is invalid")
    return value


def _scope(value: object) -> WriteScope:
    row = _exact(
        value,
        {"level", "languages", "files", "section_ids", "block_ids", "allowed_operations"},
        "write scope",
    )
    return WriteScope(
        level=row["level"],
        languages=tuple(row["languages"]),
        files=tuple(row["files"]),
        section_ids=tuple(row["section_ids"]),
        block_ids=tuple(row["block_ids"]),
        allowed_operations=tuple(row["allowed_operations"]),
    )


def _request(value: object) -> CompileRequest:
    row = _exact(
        value,
        {"targets", "write_scope", "source_mode", "shadow_transaction_id"},
        "compile request",
    )
    return CompileRequest(
        targets=tuple(row["targets"]),
        write_scope=_scope(row["write_scope"]),
        source_mode=row["source_mode"],
        shadow_transaction_id=row["shadow_transaction_id"],
    )


def _authority(value: object) -> AuthoritySnapshot:
    row = _exact(value, {"model", "mode", "hash", "transaction_id"}, "authority")
    return AuthoritySnapshot(row["model"], row["mode"], row["hash"], row["transaction_id"])


def _input(value: object) -> InputSnapshot:
    if not isinstance(value, dict):
        raise BundleVerificationError("input snapshot shape is invalid")
    allowed = {"kind", "identity", "type", "hash", "content_hash", "relation", "model", "revision"}
    required = {"kind", "identity", "type", "hash", "relation"}
    if not required.issubset(value) or not set(value).issubset(allowed):
        raise BundleVerificationError("input snapshot shape is invalid")
    return InputSnapshot(
        identity=value["identity"],
        input_type=value["type"],
        semantic_hash=value["hash"],
        relation=value["relation"],
        model_name=value.get("model", ""),
        revision=value.get("revision"),
        snapshot_kind=value["kind"],
        content_hash=value.get("content_hash", ""),
    )


def _finding(value: object) -> CompileFinding:
    row = _exact(value, {"code", "pointer", "message", "severity", "identity"}, "finding")
    return CompileFinding(**row)


def _decode_bundle(value: object) -> CompileBundle:
    row = _exact(
        value,
        {
            "schema_version", "compiler_contract_version", "compile_id", "source_mode",
            "status", "applicable", "contract_snapshot_hash", "manuscript_snapshot_hash",
            "request", "authority", "inputs", "section_plans", "writer_packets",
            "global_context", "findings",
        },
        "compile bundle",
    )
    authority = tuple(_authority(item) for item in row["authority"])
    inputs = tuple(_input(item) for item in row["inputs"])
    plans: list[SectionPlan] = []
    for value in row["section_plans"]:
        item = _exact(
            value,
            {"schema_version", "section_id", "revision", "semantic_hash", "section_kind", "ordered_block_ids", "inputs", "projection", "findings"},
            "section plan",
        )
        plans.append(
            SectionPlan(
                section_id=item["section_id"], revision=item["revision"],
                semantic_hash=item["semantic_hash"], section_kind=item["section_kind"],
                ordered_block_ids=tuple(item["ordered_block_ids"]),
                inputs=tuple(_input(value) for value in item["inputs"]),
                projection=item["projection"], findings=tuple(_finding(value) for value in item["findings"]),
                schema_version=item["schema_version"],
            )
        )
    packets: list[WriterPacket] = []
    for value in row["writer_packets"]:
        item = _exact(
            value,
            {"schema_version", "packet_id", "compile_id", "authority", "write_scope", "inputs", "read_context", "payload", "dependency_profile", "dependency_hash"},
            "Writer packet",
        )
        packets.append(
            WriterPacket(
                packet_id=item["packet_id"], compile_id=item["compile_id"],
                authority=tuple(_authority(value) for value in item["authority"]),
                write_scope=_scope(item["write_scope"]),
                inputs=tuple(_input(value) for value in item["inputs"]),
                read_context=item["read_context"], payload=item["payload"],
                dependency_profile=item["dependency_profile"], dependency_hash=item["dependency_hash"],
                schema_version=item["schema_version"],
            )
        )
    try:
        bundle = CompileBundle(
            compile_id=row["compile_id"], source_mode=row["source_mode"],
            request=_request(row["request"]), authority=authority, inputs=inputs,
            section_plans=tuple(plans), writer_packets=tuple(packets),
            findings=tuple(_finding(item) for item in row["findings"]),
            status=row["status"], schema_version=row["schema_version"],
            compiler_contract_version=row["compiler_contract_version"],
            applicable=row["applicable"], contract_snapshot_hash=row["contract_snapshot_hash"],
            manuscript_snapshot_hash=row["manuscript_snapshot_hash"], global_context=row["global_context"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BundleVerificationError("compile bundle DTO validation failed") from error
    projections = {plan.section_id: _json_compatible(plan.projection) for plan in bundle.section_plans}
    expected_id = compute_compile_id(
        compiler_contract_version=bundle.compiler_contract_version,
        source_mode=bundle.source_mode,
        applicable=bundle.applicable,
        request=bundle.request,
        authority=bundle.authority,
        inputs=bundle.inputs,
        contract_snapshot_hash=bundle.contract_snapshot_hash,
        manuscript_snapshot_hash=bundle.manuscript_snapshot_hash,
        global_context=bundle.global_context,
        section_projections=projections,
    )
    if expected_id != bundle.compile_id or bundle.to_dict() != row:
        raise BundleVerificationError("compile bundle ID or DTO round trip is inconsistent")
    return bundle


def load_verified_bundle(root: str | Path, compile_id: str) -> VerifiedBundle:
    """Load a bundle only after verifying its exact closed artifact set."""
    try:
        paths = compile_paths(root, compile_id)
    except (TypeError, ValueError) as error:
        raise BundleVerificationError("compile ID is invalid") from error
    directory = paths.compile_dir
    try:
        info = directory.lstat()
    except OSError as error:
        raise BundleVerificationError("compile bundle does not exist") from error
    if not stat.S_ISDIR(info.st_mode) or directory.is_symlink():
        raise BundleVerificationError("compile bundle directory is unsafe")
    bundle_doc, _ = _read_json_regular(paths.bundle_path)
    if set(bundle_doc) != {"schema_version", "bundle", "artifacts"}:
        raise BundleVerificationError("compile bundle envelope is not closed")
    if bundle_doc.get("schema_version") != 1 or not isinstance(bundle_doc.get("bundle"), dict):
        raise BundleVerificationError("compile bundle envelope version is invalid")
    try:
        bundle_dto = _decode_bundle(bundle_doc["bundle"])
    except BundleVerificationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise BundleVerificationError("compile bundle DTO validation failed") from error
    bundle = bundle_dto.to_dict()
    if bundle.get("compile_id") != compile_id or bundle.get("status") != "ready":
        raise BundleVerificationError("compile bundle identity is inconsistent")
    rows = _safe_artifact_rows(bundle_doc.get("artifacts"))
    expected = {"bundle.json", *(row["path"] for row in rows)}
    actual: set[str] = set()
    actual_directories: set[str] = set()
    for candidate in directory.rglob("*"):
        relative = candidate.relative_to(directory).as_posix()
        info = candidate.lstat()
        if stat.S_ISDIR(info.st_mode) and not candidate.is_symlink():
            actual_directories.add(relative)
            continue
        if not stat.S_ISREG(info.st_mode) or candidate.is_symlink():
            raise BundleVerificationError("compile directory contains an unsafe entry")
        actual.add(relative)
    if actual != expected:
        raise BundleVerificationError("compile artifact set does not match its manifest")
    expected_directories = {
        parent
        for row in rows
        for parent in (
            "/".join(row["path"].split("/")[:index])
            for index in range(1, len(row["path"].split("/")))
        )
        if parent
    }
    if actual_directories != expected_directories:
        raise BundleVerificationError("compile directory set does not match its manifest")
    documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        document, raw = _read_json_regular(directory / row["path"])
        if _hash_bytes(raw) != row["content_hash"]:
            raise BundleVerificationError("compile artifact hash does not match")
        documents[row["path"]] = document
    report = documents.get("report.json")
    if not isinstance(report, dict) or report.get("compile_id") != compile_id:
        raise BundleVerificationError("compile report identity is inconsistent")
    report_rows = _safe_artifact_rows(report.get("artifacts"))
    if tuple(row for row in rows if row["path"] != "report.json") != report_rows:
        raise BundleVerificationError("compile report manifest is inconsistent")
    plan_paths = {f"plans/{item.get('section_id')}.json" for item in bundle.get("section_plans", []) if isinstance(item, dict)}
    packet_paths = {f"packets/{item.get('packet_id')}.json" for item in bundle.get("writer_packets", []) if isinstance(item, dict)}
    if (
        not plan_paths
        or not packet_paths
        or len(plan_paths) != len(bundle.get("section_plans", []))
        or len(packet_paths) != len(bundle.get("writer_packets", []))
    ):
        raise BundleVerificationError("compile bundle products are incomplete")
    if not plan_paths.issubset(documents) or not packet_paths.issubset(documents):
        raise BundleVerificationError("compile bundle product references are missing")
    if documents.get("context/global.json") != bundle.get("global_context"):
        raise BundleVerificationError("compile global context reference is inconsistent")
    for item in bundle["section_plans"]:
        if documents[f"plans/{item['section_id']}.json"] != item:
            raise BundleVerificationError("compile section plan reference is inconsistent")
    for item in bundle["writer_packets"]:
        if documents[f"packets/{item['packet_id']}.json"] != item:
            raise BundleVerificationError("compile Writer packet reference is inconsistent")
    return VerifiedBundle(compile_id, bundle, report, rows)


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directories(root: Path) -> None:
    for directory in sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ) + [root]:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _directory_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def _materialize_from_root(root: Path, request: CompileRequest):
    loaded = load_compile_inputs(root, request)
    kinds = sorted(
        {
            str(item.document.get("section_kind"))
            for item in loaded.objects
            if item.object_type == "section" and item.object_id in request.targets
        }
    )
    contracts = CompileContractSnapshot.from_contracts(
        resolve_section_contract(root, kind) for kind in kinds
    )
    return materialize_compile(loaded, contracts, scan_manuscript(root), request)


def _ensure_state_root(project: Path, name: str) -> Path:
    paperops = project / ".paperops"
    paperops.mkdir(exist_ok=True)
    if paperops.is_symlink() or not stat.S_ISDIR(paperops.lstat().st_mode):
        raise BundleVerificationError("generated state root is unsafe")
    state_root = paperops / name
    state_root.mkdir(exist_ok=True)
    if state_root.is_symlink() or not stat.S_ISDIR(state_root.lstat().st_mode):
        raise BundleVerificationError("generated state namespace is unsafe")
    return state_root


def _write_blocked(
    root: Path,
    compile_id: str,
    applicable: bool,
    findings: tuple[CompileFinding, ...],
) -> CompileResult:
    relative = f".paperops/compile-diagnostics/{compile_id}/report.json"
    target = root / relative
    payload = {
        "schema_version": 1,
        "compile_id": compile_id,
        "status": "blocked",
        "applicable": applicable,
        "artifacts": [],
        "findings": [item.to_dict() for item in findings],
    }
    state_root = _ensure_state_root(root, "compile-diagnostics")
    target.parent.mkdir(exist_ok=True)
    if target.parent.parent != state_root or target.parent.is_symlink():
        raise BundleVerificationError("diagnostic state directory is unsafe")
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    _write_file(temporary, canonical_json_bytes(payload))
    os.replace(temporary, target)
    return CompileResult(
        compile_id,
        "blocked",
        applicable,
        findings,
        diagnostic_path=relative,
    )


def _diagnostic_result(root: Path, candidate) -> CompileResult:
    return _write_blocked(
        root,
        candidate.compile_id,
        candidate.applicable,
        candidate.findings,
    )


def prepare_bundle(
    root: str | Path,
    request: CompileRequest,
    refresh: bool = False,
) -> CompileResult:
    """Compile current authority and atomically publish a verified immutable bundle."""
    project = Path(root).expanduser().absolute()
    try:
        candidate = _materialize_from_root(project, request)
    except CompileInputError as error:
        del error
        compile_id = "compile-blocked-v1-" + semantic_hash(
            {"request": request.to_dict(), "contract": "input-error-v1"}
        ).split(":", 1)[1]
        finding = CompileFinding(
            "compile.input_invalid",
            "/request",
            "compile input could not be validated",
        )
        return _write_blocked(
            project,
            compile_id,
            request.source_mode == "authoritative",
            (finding,),
        )
    if not candidate.successful:
        return _diagnostic_result(project, candidate)
    bundle = candidate.to_bundle()
    paths = compile_paths(project, candidate.compile_id)
    state_root = _ensure_state_root(project, "compile")
    if paths.compile_dir.exists() and not refresh:
        verified = load_verified_bundle(project, candidate.compile_id)
        return CompileResult(
            candidate.compile_id,
            "ready",
            candidate.applicable,
            candidate.findings,
            verified.artifacts,
            reused=True,
        )
    stage: Path | None = Path(
        tempfile.mkdtemp(dir=state_root, prefix=f".stage-{candidate.compile_id}-")
    )
    try:
        product_bytes: dict[str, tuple[str, bytes]] = {
            "context/global.json": ("global-context", canonical_json_bytes(candidate.global_context)),
        }
        for plan in candidate.section_plans:
            product_bytes[f"plans/{plan.section_id}.json"] = ("section-plan", canonical_json_bytes(plan))
        for packet in candidate.writer_packets:
            product_bytes[f"packets/{packet.packet_id}.json"] = ("writer-packet", canonical_json_bytes(packet))
        report_rows = tuple(
            _artifact(path, kind, content)
            for path, (kind, content) in sorted(product_bytes.items())
        )
        report = {
            "schema_version": 1,
            "compile_id": candidate.compile_id,
            "status": candidate.status,
            "applicable": candidate.applicable,
            "artifacts": list(report_rows),
            "findings": [item.to_dict() for item in candidate.findings],
        }
        report_bytes = canonical_json_bytes(report)
        all_rows = tuple((*report_rows, _artifact("report.json", "report", report_bytes)))
        envelope = {
            "schema_version": 1,
            "bundle": bundle.to_dict(),
            "artifacts": list(all_rows),
        }
        for path, (_, content) in product_bytes.items():
            _write_file(stage / path, content)
        _write_file(stage / "report.json", report_bytes)
        _write_file(stage / "bundle.json", canonical_json_bytes(envelope))
        _fsync_directories(stage)
        if paths.compile_dir.exists():
            existing: VerifiedBundle | None
            try:
                existing = load_verified_bundle(project, candidate.compile_id)
            except BundleVerificationError:
                existing = None
            if existing is not None:
                if _directory_bytes(stage) != _directory_bytes(paths.compile_dir):
                    raise BundleVerificationError(
                        "identical compile ID produced different artifact bytes"
                    )
                shutil.rmtree(stage)
                stage = None
                return CompileResult(
                    candidate.compile_id,
                    "ready",
                    candidate.applicable,
                    candidate.findings,
                    existing.artifacts,
                    reused=not refresh,
                    refreshed=refresh,
                )
            if not refresh:
                raise BundleVerificationError("existing compile bundle is corrupt")
            quarantine = state_root / f".corrupt-{candidate.compile_id}-{os.getpid()}"
            os.rename(paths.compile_dir, quarantine)
            try:
                os.rename(stage, paths.compile_dir)
                stage = None
                _fsync_directory(state_root)
            except BaseException:
                os.rename(quarantine, paths.compile_dir)
                raise
            shutil.rmtree(quarantine)
            _fsync_directory(state_root)
        else:
            try:
                os.rename(stage, paths.compile_dir)
                stage = None
            except OSError as error:
                if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                    raise
                verified = load_verified_bundle(project, candidate.compile_id)
                return CompileResult(
                    candidate.compile_id,
                    "ready",
                    candidate.applicable,
                    candidate.findings,
                    verified.artifacts,
                    reused=True,
                )
            _fsync_directory(state_root)
        verified = load_verified_bundle(project, candidate.compile_id)
        return CompileResult(
            candidate.compile_id,
            "ready",
            candidate.applicable,
            candidate.findings,
            verified.artifacts,
            refreshed=refresh,
        )
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)


def _inspect_compile_entry(root: str | Path, compile_id: str) -> CompileResult:
    verified = load_verified_bundle(root, compile_id)
    bundle = verified.bundle
    findings = tuple(
        CompileFinding(**item) for item in bundle.get("findings", [])
    )
    return CompileResult(
        compile_id,
        str(bundle["status"]),
        bool(bundle["applicable"]),
        findings,
        verified.artifacts,
        reused=True,
    )


def inspect_compile(
    root: str | Path,
    target_or_all: str = "all",
) -> CompileCacheStatus:
    """Inspect verified cache entries matching a section target, without writes."""
    project = Path(root).expanduser().absolute()
    state_root = project / ".paperops/compile"
    results: list[CompileResult] = []
    findings: list[CompileFinding] = []
    if state_root.is_symlink() or (state_root.exists() and not state_root.is_dir()):
        findings.append(
            CompileFinding(
                "compile.cache_invalid",
                "/cache",
                "compile cache namespace is invalid",
            )
        )
    elif state_root.is_dir():
        for entry in sorted(state_root.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            try:
                verified = load_verified_bundle(project, entry.name)
                inspected = _inspect_compile_entry(project, entry.name)
            except BundleVerificationError:
                findings.append(
                    CompileFinding(
                        "compile.cache_invalid",
                        f"/cache/{len(findings)}",
                        "a compile cache entry is invalid",
                    )
                )
                continue
            targets = verified.bundle["request"]["targets"]
            if target_or_all == "all" or target_or_all in targets:
                results.append(inspected)
    return CompileCacheStatus(target_or_all, tuple(results), tuple(findings))


__all__ = [
    "BundleVerificationError",
    "CompileCacheStatus",
    "CompileResult",
    "VerifiedBundle",
    "inspect_compile",
    "load_verified_bundle",
    "prepare_bundle",
]
