"""Safe full-manuscript Writer workspaces with exact scoped patch extraction."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from .bundles import BundleVerificationError, load_verified_bundle
from .conservation import analyze_patch
from .patches import WriterPatchResult
from .privacy import contains_private_tex_material
from .safe_fs import SafeCaptureError, SafeProjectReader
from .storage import atomic_write_json, canonical_json_bytes, semantic_hash
from .tex import parse_tex_bytes
from .types import CompileFinding, _freeze_json, _json_compatible, _validate_id


_BUILD_PREFIX = "manuscript/shared/build/"
_STANDARD_CITATIONS = {
    "autocite", "cite", "citealp", "citeauthor", "citep", "citet", "cites",
    "citeyear", "citeyearpar", "footcite", "nocite", "parencite", "parencites",
    "smartcite", "supercite", "textcite", "textcites",
}
_CITE_LIKE = re.compile(r"\\(?P<command>[A-Za-z]*cite[A-Za-z]*)\*?")


def _hash_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class WriterSessionResult:
    session_id: str
    compile_id: str
    status: str
    applicable: bool
    source_mode: str
    base_manifest_hash: str
    findings: tuple[CompileFinding, ...] = ()
    reused: bool = False
    schema_version: int = 1

    @property
    def ok(self) -> bool:
        return self.status == "ready" and not any(
            item.severity == "error" for item in self.findings
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "compile_id": self.compile_id,
            "status": self.status,
            "applicable": self.applicable,
            "source_mode": self.source_mode,
            "base_manifest_hash": self.base_manifest_hash,
            "reused": self.reused,
            "workspace": f".paperops/writer/{self.session_id}/workspace/manuscript",
            "findings": [item.to_dict() for item in self.findings],
        }


def _finding(code: str, pointer: str, message: str) -> CompileFinding:
    return CompileFinding(code, pointer, message)


def _state_root(project: Path) -> Path:
    paperops = project / ".paperops"
    paperops.mkdir(exist_ok=True)
    if paperops.is_symlink() or not stat.S_ISDIR(paperops.lstat().st_mode):
        raise SafeCaptureError("Writer state root is unsafe")
    writer = paperops / "writer"
    writer.mkdir(exist_ok=True)
    if writer.is_symlink() or not stat.S_ISDIR(writer.lstat().st_mode):
        raise SafeCaptureError("Writer state namespace is unsafe")
    return writer


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    for path in sorted((item for item in root.rglob("*") if item.is_file())):
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    directories = sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    )
    for directory in (*directories, root):
        _fsync_directory(directory)


def _capture(root: Path, destination: Path):
    with SafeProjectReader(root) as reader:
        captured = reader.copy_entry("manuscript", destination / "manuscript")
    return captured


def _file_rows(captured) -> list[dict[str, object]]:
    return [
        {
            "identity": item.identity,
            "type": "regular",
            "content_hash": item.content_hash,
            "size": item.size,
            "mode": item.mode,
        }
        for item in sorted(captured, key=lambda row: row.identity)
    ]


def _bindings(bundle: Mapping[str, Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    model_inputs = {
        str(item.get("identity", "")).rsplit("/", 1)[-1].removesuffix(".yml"): item
        for item in bundle.get("inputs", ())
        if isinstance(item, Mapping)
        and item.get("type") == "block"
    }
    context = bundle.get("global_context", {})
    for section in context.get("section_block_map", ()):
        if not isinstance(section, Mapping):
            continue
        for block in section.get("blocks", ()):
            if not isinstance(block, Mapping):
                continue
            for binding in block.get("bindings", ()):
                if not isinstance(binding, Mapping):
                    continue
                typed_id = str(binding.get("typed_block_id", ""))
                model_input = model_inputs.get(typed_id, {})
                rows.append(
                    {
                        **dict(binding),
                        "section_id": block.get("section_id", ""),
                        "operation": block.get("operation", ""),
                        "allowed_operations": list(block.get("allowed_operations", ())),
                        "claim_refs": list(block.get("claim_refs", ())),
                        "result_refs": list(block.get("result_refs", ())),
                        "figure_refs": list(block.get("figure_refs", ())),
                        "citation_keys": list(block.get("citation_keys", ())),
                        "move_bindings": list(section.get("move_bindings", ())),
                        "model_revision": model_input.get("revision", 0),
                        "model_hash": model_input.get("hash", ""),
                        "authorization_reason": "current typed Manuscript block plan",
                    }
                )
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("file_identity", "")),
            int(row.get("marker_index", 0)),
            str(row.get("typed_block_id", "")),
        ),
    )


def _tex_inventory(workspace: Path, files: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in files:
        identity = str(item["identity"])
        if not identity.endswith(".tex"):
            continue
        snapshot = parse_tex_bytes(identity, (workspace / identity).read_bytes())
        rows.append(snapshot.to_dict())
    return rows


def start_writer_session(root: str | Path, compile_id: str) -> WriterSessionResult:
    project = Path(root).expanduser().absolute()
    verified = load_verified_bundle(project, compile_id)
    bundle = verified.bundle
    state_root = _state_root(project)
    session_id = "writer-v1-" + secrets.token_hex(16)
    stage: Path | None = Path(
        tempfile.mkdtemp(dir=state_root, prefix=f".stage-{session_id}-")
    )
    os.chmod(stage, 0o700)
    try:
        workspace = stage / "workspace"
        captured = _capture(project, workspace)
        files = _file_rows(captured)
        with tempfile.TemporaryDirectory(prefix="pops-writer-verify-") as temporary:
            repeated = _capture(project, Path(temporary))
            if _file_rows(repeated) != files:
                raise SafeCaptureError("living manuscript changed during Writer snapshot")
        bundle_hash = semantic_hash(
            {
                "schema_version": 1,
                "bundle": _json_compatible(bundle),
                "artifacts": [_json_compatible(item) for item in verified.artifacts],
            }
        )
        manifest = {
            "schema_version": 1,
            "compile_id": compile_id,
            "bundle_hash": bundle_hash,
            "source_mode": bundle["source_mode"],
            "applicable": bundle["applicable"],
            "authority": _json_compatible(bundle["authority"]),
            "write_scope": _json_compatible(bundle["request"]["write_scope"]),
            "files": files,
            "tex_files": _tex_inventory(workspace, files),
            "bindings": _bindings(bundle),
            "section_topology": _json_compatible(
                bundle.get("global_context", {}).get("section_block_map", ())
            ),
            "extensions": {},
        }
        manifest_hash = semantic_hash(manifest)
        session = {
            "schema_version": 1,
            "session_id": session_id,
            "compile_id": compile_id,
            "bundle_hash": bundle_hash,
            "base_manifest_hash": manifest_hash,
            "source_mode": bundle["source_mode"],
            "applicable": bundle["applicable"],
            "extensions": {},
        }
        atomic_write_json(stage / "base-manifest.json", manifest)
        atomic_write_json(stage / "session.json", session)
        (stage / "transactions").mkdir()
        _fsync_tree(stage)
        target = state_root / session_id
        os.rename(stage, target)
        stage = None
        _fsync_directory(state_root)
        return WriterSessionResult(
            session_id,
            compile_id,
            "ready",
            bool(bundle["applicable"]),
            str(bundle["source_mode"]),
            manifest_hash,
        )
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)


def _read_canonical(path: Path) -> dict[str, Any]:
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SafeCaptureError("Writer session state is not a regular file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            raw = stream.read()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SafeCaptureError("Writer session state is unreadable") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise SafeCaptureError("Writer session state is not canonical")
    return value


def _session_state(project: Path, session_id: str):
    _validate_id(session_id, "Writer session ID")
    directory = project / ".paperops/writer" / session_id
    if directory.is_symlink() or not directory.is_dir():
        raise SafeCaptureError("Writer session is missing or unsafe")
    session = _read_canonical(directory / "session.json")
    manifest = _read_canonical(directory / "base-manifest.json")
    if (
        session.get("session_id") != session_id
        or session.get("compile_id") != manifest.get("compile_id")
        or session.get("base_manifest_hash") != semantic_hash(manifest)
    ):
        raise SafeCaptureError("Writer session binding is invalid")
    verified = load_verified_bundle(project, str(session["compile_id"]))
    expected_bundle_hash = semantic_hash(
        {
            "schema_version": 1,
            "bundle": _json_compatible(verified.bundle),
            "artifacts": [_json_compatible(item) for item in verified.artifacts],
        }
    )
    if (
        session.get("bundle_hash") != expected_bundle_hash
        or manifest.get("bundle_hash") != expected_bundle_hash
        or session.get("source_mode") != verified.bundle.get("source_mode")
        or session.get("applicable") != verified.bundle.get("applicable")
        or manifest.get("source_mode") != verified.bundle.get("source_mode")
        or manifest.get("applicable") != verified.bundle.get("applicable")
        or manifest.get("authority")
        != _json_compatible(verified.bundle.get("authority"))
        or manifest.get("write_scope")
        != _json_compatible(
            verified.bundle.get("request", {}).get("write_scope")
        )
    ):
        raise SafeCaptureError("Writer session compile binding is invalid")
    transactions = directory / "transactions"
    if transactions.is_symlink() or not transactions.is_dir():
        raise SafeCaptureError("Writer transaction namespace is unsafe")
    return directory, session, manifest, verified


def inspect_writer_session(root: str | Path, session_id: str) -> WriterSessionResult:
    project = Path(root).expanduser().absolute()
    directory, session, manifest, _verified = _session_state(project, session_id)
    workspace = directory / "workspace/manuscript"
    findings: tuple[CompileFinding, ...] = ()
    if workspace.is_symlink() or not workspace.is_dir():
        findings = (
            _finding("write.workspace_invalid", "/workspace", "Writer workspace is missing or unsafe"),
        )
    return WriterSessionResult(
        session_id,
        str(session["compile_id"]),
        "ready" if not findings else "blocked",
        bool(session["applicable"]),
        str(session["source_mode"]),
        str(session["base_manifest_hash"]),
        findings,
        reused=True,
    )


def _captured_map(captured) -> dict[str, dict[str, object]]:
    return {row["identity"]: row for row in _file_rows(captured)}


def _tex_map(rows: object) -> dict[str, Mapping[str, Any]]:
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("identity")): row
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("identity"), str)
    }


def _snapshot_hash(files: Mapping[str, Mapping[str, object]]) -> str:
    return semantic_hash([files[key] for key in sorted(files)])


def _candidate_context(
    candidate_root: Path,
    candidate: Mapping[str, Mapping[str, object]],
    bundle: Mapping[str, Any],
) -> dict[str, object]:
    tex_files: list[dict[str, object]] = []
    custom_commands: set[str] = set()
    privacy_violation = False
    terminology_violation = False
    prohibitions = bundle.get("global_context", {}).get("terminology", {}).get(
        "prohibitions",
        (),
    )
    forbidden_terms = {
        term
        for row in prohibitions
        if isinstance(row, Mapping)
        for term in (
            row.get("ja"),
            row.get("en_public"),
            *row.get("avoid", ()),
        )
        if isinstance(term, str) and term.strip()
    }
    for identity in sorted(candidate):
        if not identity.endswith(".tex"):
            continue
        content = (candidate_root / identity).read_bytes()
        snapshot = parse_tex_bytes(identity, content)
        tex_files.append(snapshot.to_dict())
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        custom_commands.update(
            match.group("command")
            for match in _CITE_LIKE.finditer(text)
            if match.group("command") not in _STANDARD_CITATIONS
        )
        privacy_violation = privacy_violation or contains_private_tex_material(text)
        terminology_violation = terminology_violation or any(
            term in text for term in forbidden_terms
        )
    return {
        "tex_files": tex_files,
        "custom_citation_commands": sorted(custom_commands),
        "privacy_violation": privacy_violation,
        "terminology_violation": terminology_violation,
    }


def _patch_from_candidate(
    session_id: str,
    session: Mapping[str, Any],
    manifest: Mapping[str, Any],
    live: Mapping[str, Mapping[str, object]],
    candidate: Mapping[str, Mapping[str, object]],
    candidate_root: Path,
) -> WriterPatchResult:
    findings: list[CompileFinding] = []
    base = {
        str(row["identity"]): row
        for row in manifest.get("files", ())
        if isinstance(row, Mapping) and isinstance(row.get("identity"), str)
    }
    comparable = lambda identity: not identity.startswith(_BUILD_PREFIX)
    if {
        key: value for key, value in live.items() if comparable(key)
    } != {
        key: value for key, value in base.items() if comparable(key)
    }:
        findings.append(
            _finding("write.base_drift", "/base", "living manuscript changed after Writer session start")
        )
    added = sorted(set(candidate) - set(base))
    removed = sorted(set(base) - set(candidate))
    replan = False
    for identity in (*added, *removed):
        if comparable(identity):
            findings.append(
                _finding("write.scope_violation", "/topology", "candidate file topology is outside write scope")
            )
    changed_files = sorted(
        identity
        for identity in set(base) & set(candidate)
        if comparable(identity) and base[identity] != candidate[identity]
    )
    scope = manifest.get("write_scope", {})
    selected_blocks = set(scope.get("block_ids", ())) if isinstance(scope, Mapping) else set()
    scoped_files = set(scope.get("files", ())) if isinstance(scope, Mapping) else set()
    bindings = [row for row in manifest.get("bindings", ()) if isinstance(row, Mapping)]
    binding_by_raw = {
        (str(row.get("file_identity")), str(row.get("raw_block_id"))): row
        for row in bindings
    }
    base_tex = _tex_map(manifest.get("tex_files"))
    target_files: list[dict[str, object]] = []
    changes: list[dict[str, object]] = []
    for identity in changed_files:
        target_files.append(
            {
                "identity": identity,
                "preimage": dict(base[identity]),
                "candidate": dict(candidate[identity]),
            }
        )
        if identity not in scoped_files or not identity.endswith(".tex"):
            findings.append(
                _finding("write.scope_violation", "/files", "candidate changed a file outside write scope")
            )
            continue
        parsed = parse_tex_bytes(identity, (candidate_root / identity).read_bytes())
        if any(item.severity == "error" for item in parsed.findings):
            findings.append(
                _finding("write.candidate_invalid", "/candidate", "candidate TeX structure is invalid")
            )
            continue
        base_row = base_tex.get(identity, {})
        base_blocks = {
            str(row.get("marker_id")): row
            for row in base_row.get("blocks", ())
            if isinstance(row, Mapping)
        }
        candidate_blocks = {row.marker_id: row for row in parsed.blocks}
        added_markers = set(candidate_blocks) - set(base_blocks)
        removed_markers = set(base_blocks) - set(candidate_blocks)
        file_change_count = 0
        unplanned_added = False
        for raw_id in sorted(added_markers):
            binding = binding_by_raw.get((identity, raw_id))
            candidate_block = candidate_blocks[raw_id]
            authorized = (
                binding is not None
                and str(binding.get("typed_block_id")) in selected_blocks
                and str(binding.get("operation", "")) == "add"
                and "add" in set(binding.get("allowed_operations", ()))
            )
            if not authorized:
                unplanned_added = True
                replan = True
                findings.append(
                    _finding("write.replan_required", "/blocks", "candidate adds an unplanned block marker")
                )
                continue
            file_change_count += 1
            changes.append(
                {
                    "typed_block_id": binding.get("typed_block_id", ""),
                    "raw_block_id": raw_id,
                    "operation": "add",
                    "from": None,
                    "to": {"file": identity, "position": candidate_block.marker_index},
                    "base": None,
                    "candidate": {
                        "marker_hash": candidate_block.marker_hash,
                        "body_hash": candidate_block.body_hash,
                        "region_hash": candidate_block.region_hash,
                    },
                    "model_revision": binding.get("model_revision", 0),
                    "model_hash": binding.get("model_hash", ""),
                    "authorization": "add",
                    "reason": binding.get("authorization_reason", ""),
                }
            )
        for raw_id in sorted(set(base_blocks) | set(candidate_blocks)):
            binding = binding_by_raw.get((identity, raw_id))
            base_block = base_blocks.get(raw_id)
            candidate_block = candidate_blocks.get(raw_id)
            if raw_id in added_markers:
                continue
            if (
                unplanned_added
                and candidate_block is not None
                and base_block.get("marker_index") == candidate_block.marker_index
                and base_block.get("marker_hash") == candidate_block.marker_hash
            ):
                continue
            changed = candidate_block is None or any(
                base_block.get(field) != getattr(candidate_block, field)
                for field in ("marker_index", "marker_hash", "body_hash")
            )
            if not changed:
                continue
            file_change_count += 1
            position_only = (
                candidate_block is not None
                and base_block.get("marker_hash") == candidate_block.marker_hash
                and base_block.get("body_hash") == candidate_block.body_hash
                and base_block.get("marker_index") != candidate_block.marker_index
            )
            if binding is None or str(binding.get("typed_block_id")) not in selected_blocks:
                if position_only:
                    continue
                findings.append(
                    _finding("write.scope_violation", "/blocks", "candidate changed a block outside write scope")
                )
                continue
            operation = "cut" if candidate_block is None else (
                "move" if base_block.get("marker_index") != candidate_block.marker_index else "rewrite"
            )
            allowed = set(binding.get("allowed_operations", ()))
            planned = str(binding.get("operation", ""))
            if operation not in allowed or (operation != "rewrite" and planned != operation):
                replan = True
                findings.append(
                    _finding("write.replan_required", "/blocks", "candidate topology change is not authorized by the current model")
                )
            changes.append(
                {
                    "typed_block_id": binding.get("typed_block_id", ""),
                    "raw_block_id": raw_id,
                    "operation": operation,
                    "from": {
                        "file": identity,
                        "position": base_block.get("marker_index"),
                    },
                    "to": None if candidate_block is None else {
                        "file": identity,
                        "position": candidate_block.marker_index,
                    },
                    "base": {
                        "marker_hash": base_block.get("marker_hash", ""),
                        "body_hash": base_block.get("body_hash", ""),
                        "region_hash": base_block.get("region_hash", ""),
                    },
                    "candidate": None if candidate_block is None else {
                        "marker_hash": candidate_block.marker_hash,
                        "body_hash": candidate_block.body_hash,
                        "region_hash": candidate_block.region_hash,
                    },
                    "model_revision": binding.get("model_revision", 0),
                    "model_hash": binding.get("model_hash", ""),
                    "authorization": planned,
                    "reason": binding.get("authorization_reason", ""),
                }
            )
        if file_change_count == 0 and not added_markers:
            findings.append(
                _finding("write.scope_violation", "/preamble", "candidate changed TeX outside typed blocks")
            )
    has_error = any(item.severity == "error" for item in findings)
    status = "replan_required" if replan and not any(
        item.code in {"write.base_drift", "write.scope_violation", "write.candidate_invalid"}
        for item in findings
    ) else "blocked" if has_error else "ready"
    result = WriterPatchResult(
        session_id=session_id,
        compile_id=str(session["compile_id"]),
        status=status,
        applicable=bool(session["applicable"]),
        source_mode=str(session["source_mode"]),
        base_manifest_hash=str(session["base_manifest_hash"]),
        candidate_snapshot_hash=_snapshot_hash(candidate),
        authority=tuple(manifest.get("authority", ())),
        write_scope=manifest.get("write_scope", {}),
        target_files=tuple(target_files),
        changes=tuple(changes),
        findings=tuple(findings),
        conservation_result="pending" if status == "ready" else "blocked",
    )
    return replace(result, patch_hash=semantic_hash(result._payload()))


def build_patch(root: str | Path, session_id: str) -> WriterPatchResult:
    project = Path(root).expanduser().absolute()
    _validate_id(session_id, "Writer session ID")
    session_directory = project / ".paperops/writer" / session_id
    if session_directory.is_symlink() or not session_directory.is_dir():
        raise SafeCaptureError("Writer session is missing or unsafe")
    stale_patch = session_directory / "patch.json"
    stale_patch.unlink(missing_ok=True)
    directory, session, manifest, verified = _session_state(project, session_id)
    candidate_files: dict[str, dict[str, object]] = {}
    live_files: dict[str, dict[str, object]] = {}
    temporary = tempfile.TemporaryDirectory(prefix="pops-writer-patch-")
    try:
        base = Path(temporary.name)
        live_capture = _capture(project, base / "live")
        live_files = _captured_map(live_capture)
        workspace = directory / "workspace"
        candidate_capture = _capture(workspace, base / "candidate")
        candidate_files = _captured_map(candidate_capture)
        candidate_root = base / "candidate"
        result = _patch_from_candidate(
            session_id,
            session,
            manifest,
            live_files,
            candidate_files,
            candidate_root,
        )
        if result.status == "ready":
            analysis = analyze_patch(
                verified.bundle,
                manifest,
                _candidate_context(candidate_root, candidate_files, verified.bundle),
                result,
            )
            combined = tuple((*result.findings, *analysis.findings))
            blocked = any(item.severity == "error" for item in combined)
            result = replace(
                result,
                status="blocked" if blocked else "ready",
                findings=combined,
                proposed_dispositions=analysis.dispositions,
                introduced_references=analysis.introduced_references,
                mirror_impacts=analysis.mirror_impacts,
                conservation_result="blocked" if blocked else "passed",
                patch_hash="",
            )
            result = replace(result, patch_hash=semantic_hash(result._payload()))
    except (SafeCaptureError, OSError, ValueError, BundleVerificationError):
        result = WriterPatchResult(
            session_id=session_id,
            compile_id=str(session["compile_id"]),
            status="blocked",
            applicable=bool(session["applicable"]),
            source_mode=str(session["source_mode"]),
            base_manifest_hash=str(session["base_manifest_hash"]),
            candidate_snapshot_hash=semantic_hash([]),
            authority=tuple(manifest.get("authority", ())),
            write_scope=manifest.get("write_scope", {}),
            target_files=(),
            changes=(),
            findings=(
                _finding("write.candidate_invalid", "/candidate", "Writer candidate is missing or unsafe"),
            ),
            conservation_result="blocked",
        )
        result = replace(result, patch_hash=semantic_hash(result._payload()))
    finally:
        temporary.cleanup()
    atomic_write_json(directory / "patch.json", result.to_dict())
    _fsync_directory(directory)
    return result


__all__ = [
    "WriterSessionResult",
    "build_patch",
    "inspect_writer_session",
    "start_writer_session",
]
