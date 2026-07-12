"""Build, validate, and cache content-addressed six-model change plans."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

import yaml

from paperops.model_state import HASH_PATTERN, MODEL_NAMES, read_model_states
from paperops.model_validation import run_model_validation
from paperops.workflow_v2.mutation import canonical_json, raw_hash

from .catalog import CatalogError, identity_for, index_identity, model_entry, semantic_hash, yaml_bytes
from .request import ChangeRequestError, load_change_request
from .types import ChangePlan, Operation, Replacement


class ChangePlanningError(ValueError):
    pass


CHANGE_ID_PATTERN = re.compile(r"^CHG-[0-9a-f]{20}$")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cache_root(root: Path, *, create: bool) -> Path:
    current = root
    for name in (".paperops", "changes"):
        current = current / name
        if current.is_symlink():
            raise ChangePlanningError("change cache path is unsafe")
        if not current.exists():
            if not create:
                raise ChangePlanningError("change plan cache is missing or corrupt")
            current.mkdir(mode=0o700)
            _fsync_directory(current.parent)
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ChangePlanningError("change cache path is unsafe")
    return current


def _change_directory(root: Path, change_id: str, *, create_base: bool) -> Path:
    if not isinstance(change_id, str) or CHANGE_ID_PATTERN.fullmatch(change_id) is None:
        raise ChangePlanningError("invalid change id")
    base = _cache_root(root, create=create_base)
    directory = base / change_id
    if directory.exists() or directory.is_symlink():
        metadata = directory.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ChangePlanningError("change cache path is unsafe")
    elif not create_base:
        raise ChangePlanningError("change plan cache is missing or corrupt")
    return directory


def _write_json(path: Path, value: Any) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, canonical_json(value, pretty=True).encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_json(path: Path) -> Any:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise ChangePlanningError("change plan cache leaf is unsafe")
        with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
            descriptor = -1
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ChangePlanningError("change plan cache is missing, unsafe, or corrupt") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ChangePlanningError("typed model document is missing or invalid") from exc
    if not isinstance(value, dict):
        raise ChangePlanningError("typed model document must be a mapping")
    return value


def _current(root: Path, operation: Operation) -> tuple[str, dict[str, Any] | None, int | None, str]:
    identity = identity_for(root, operation.model, operation.record_type, operation.object_id)
    path = root.joinpath(*identity.split("/"))
    if not path.exists():
        return identity, None, None, ""
    if path.is_symlink() or not path.is_file():
        raise ChangePlanningError("typed model target is not a regular file")
    document = _read_yaml(path)
    entry = model_entry(root, operation.model)
    revision = document.get("revision", 0)
    digest = semantic_hash(root, operation.model, operation.record_type, document)
    if entry.get("document_kind") == "index":
        index = _read_yaml(root / str(entry["default_path"]))
        rows = [row for row in index.get("records", []) if isinstance(row, dict) and row.get("id") == operation.object_id]
        if len(rows) != 1 or rows[0].get("document") != identity:
            raise ChangePlanningError("typed record/index identity is inconsistent")
        revision = rows[0].get("expected_revision")
        if rows[0].get("expected_hash") != digest:
            raise ChangePlanningError("typed record/index hash is inconsistent")
    return identity, document, revision if isinstance(revision, int) else None, digest


def _check_precondition(operation: Operation, current: dict[str, Any] | None, revision: int | None, digest: str) -> None:
    expected_existing = operation.expected_revision is not None
    if current is None and expected_existing:
        raise ChangePlanningError("change precondition expected an existing object")
    if current is not None and not expected_existing:
        raise ChangePlanningError("new-object operation conflicts with an existing object")
    if current is not None and (revision != operation.expected_revision or digest != operation.expected_hash):
        raise ChangePlanningError("change precondition revision/hash drifted")
    if operation.document is not None:
        candidate_revision = operation.document.get("revision")
        if expected_existing and current is not None and "revision" in current and candidate_revision != revision + 1:
            raise ChangePlanningError("updated document revision must increment by one")
        if expected_existing and current is not None and "revision" not in current and candidate_revision is not None:
            raise ChangePlanningError("revisionless aggregate must remain revisionless")
        if not expected_existing and candidate_revision is not None and candidate_revision not in {0, 1}:
            raise ChangePlanningError("new document revision must start at zero or one")


def _index_candidate(root: Path, operation: Operation, identity: str, document: dict[str, Any] | None) -> tuple[str, bytes, bytes]:
    index_name = index_identity(root, operation.model)
    if index_name is None:
        raise ChangePlanningError("indexed candidate requested for aggregate model")
    path = root / index_name
    before = path.read_bytes()
    index = _read_yaml(path)
    records = index.get("records")
    if not isinstance(records, list):
        raise ChangePlanningError("model index records are invalid")
    records[:] = [row for row in records if not (isinstance(row, dict) and row.get("id") == operation.object_id)]
    if document is not None:
        records.append({
            "id": operation.object_id,
            "record_type": operation.record_type,
            "document": identity,
            "expected_revision": document.get("revision", 0),
            "expected_hash": semantic_hash(root, operation.model, operation.record_type, document),
        })
    records.sort(key=lambda row: str(row.get("id", "")))
    index["index_revision"] = int(index.get("index_revision", 0)) + 1
    return index_name, before, yaml_bytes(index)


def _finding_keys(result: Any, severity: str) -> set[tuple[str, str]]:
    return {(finding.code, finding.pointer) for finding in result.findings if finding.severity == severity}


def _serialize_operation(operation: Operation) -> dict[str, Any]:
    return {
        "action": operation.action, "model": operation.model,
        "record_type": operation.record_type, "id": operation.object_id,
        "expected_revision": operation.expected_revision,
        "expected_hash": operation.expected_hash,
        "candidate_revision": operation.candidate_revision,
        "candidate_hash": raw_hash(yaml_bytes(dict(operation.document))) if operation.document is not None else "",
    }


def plan_change(root: Path, request_path: Path) -> ChangePlan:
    root = root.expanduser().resolve()
    try:
        request = load_change_request(request_path)
        states = read_model_states(root)
    except (ChangeRequestError, ValueError, OSError) as exc:
        raise ChangePlanningError(str(exc)) from exc
    if any(state.mode != "v2-authoritative" for state in states.values()):
        raise ChangePlanningError("pops change requires all six models to be v2-authoritative")
    baseline = run_model_validation(root, "all", strict=False)
    if not baseline.ok:
        raise ChangePlanningError("current six-model authority is invalid")
    if any(baseline.hashes.get(name) != states[name].current_hash for name in MODEL_NAMES):
        raise ChangePlanningError("manifest model hash drifted from current authority")
    replacements: dict[str, Replacement] = {}
    resolved_identities: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="paperops-change-") as tmp:
        candidate_root = Path(tmp) / "candidate"
        shutil.copytree(root, candidate_root, symlinks=True, ignore=shutil.ignore_patterns(".paperops"))
        for operation in request.operations:
            try:
                resolved_identity = identity_for(candidate_root, operation.model, operation.record_type, operation.object_id)
                if resolved_identity in resolved_identities:
                    raise ChangePlanningError("request contains duplicate registry-resolved target identity")
                resolved_identities.add(resolved_identity)
                identity, current, revision, digest = _current(candidate_root, operation)
            except (CatalogError, OSError) as exc:
                raise ChangePlanningError(str(exc)) from exc
            _check_precondition(operation, current, revision, digest)
            before = candidate_root.joinpath(*identity.split("/")).read_bytes() if current is not None else None
            content = yaml_bytes(dict(operation.document)) if operation.document is not None else None
            replacements[identity] = Replacement(identity, raw_hash(before) if before is not None else "", raw_hash(content) if content is not None else "", content)
            target = candidate_root.joinpath(*identity.split("/"))
            if content is None:
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            if index_identity(candidate_root, operation.model) is not None:
                index_name, index_before, index_after = _index_candidate(candidate_root, operation, identity, dict(operation.document) if operation.document is not None else None)
                existing = replacements.get(index_name)
                base_before = existing.before_hash if existing else raw_hash(index_before)
                replacements[index_name] = Replacement(index_name, base_before, raw_hash(index_after), index_after)
                (candidate_root / index_name).write_bytes(index_after)
        candidate = run_model_validation(candidate_root, "all", strict=False)
        errors = _finding_keys(candidate, "error")
        new_warnings = _finding_keys(candidate, "warning") - _finding_keys(baseline, "warning")
        if not candidate.ok or errors or new_warnings:
            codes = sorted({code for code, _ in errors | new_warnings})
            raise ChangePlanningError("candidate six-model validation failed: " + ", ".join(codes))
        candidate_hashes = {name: candidate.hashes[name] for name in MODEL_NAMES}
    summary = {
        "schema_version": 1,
        "reason": request.reason,
        "operations": [_serialize_operation(item) for item in request.operations],
        "base_model_hashes": {name: states[name].current_hash for name in MODEL_NAMES},
        "candidate_model_hashes": candidate_hashes,
        "replacements": [{"identity": item.identity, "before_hash": item.before_hash, "after_hash": item.after_hash} for item in sorted(replacements.values(), key=lambda row: row.identity)],
    }
    change_id = "CHG-" + hashlib.sha256(canonical_json(summary).encode()).hexdigest()[:20]
    summary["change_id"] = change_id
    directory = _change_directory(root, change_id, create_base=True)
    plan_path = directory / "plan.json"
    payload_path = directory / "payload.json"
    if directory.exists():
        cached = read_change_plan(root, change_id)
        if canonical_json({key: value for key, value in summary.items()}) != canonical_json(_read_json(plan_path)):
            raise ChangePlanningError("change plan cache is corrupt")
        return cached
    payload = {item.identity: base64.b64encode(item.content).decode() if item.content is not None else None for item in replacements.values()}
    base = directory.parent
    staging = Path(tempfile.mkdtemp(prefix=f".{change_id}.", dir=base))
    try:
        _write_json(staging / "plan.json", summary)
        _write_json(staging / "payload.json", payload)
        _fsync_directory(staging)
        try:
            os.rename(staging, directory)
        except FileExistsError:
            return read_change_plan(root, change_id)
        _fsync_directory(base)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return read_change_plan(root, change_id)


def read_change_plan(root: Path, change_id: str) -> ChangePlan:
    directory = _change_directory(root.expanduser().resolve(), change_id, create_base=False)
    plan = _read_json(directory / "plan.json")
    payload = _read_json(directory / "payload.json")
    required = {"schema_version", "reason", "operations", "base_model_hashes", "candidate_model_hashes", "replacements", "change_id"}
    if not isinstance(plan, dict) or set(plan) != required or plan.get("schema_version") != 1 or plan.get("change_id") != change_id or not isinstance(plan.get("reason"), str) or not isinstance(payload, dict):
        raise ChangePlanningError("change plan cache identity is corrupt")
    digest_input = dict(plan); digest_input.pop("change_id")
    expected = "CHG-" + hashlib.sha256(canonical_json(digest_input).encode()).hexdigest()[:20]
    if expected != change_id:
        raise ChangePlanningError("change plan content hash is corrupt")
    operations = plan.get("operations")
    replacement_rows = plan.get("replacements")
    base_hashes = plan.get("base_model_hashes")
    candidate_hashes = plan.get("candidate_model_hashes")
    if not isinstance(operations, list) or not operations or not isinstance(replacement_rows, list):
        raise ChangePlanningError("change plan cache shape is corrupt")
    for hashes in (base_hashes, candidate_hashes):
        if not isinstance(hashes, dict) or set(hashes) != set(MODEL_NAMES) or any(
            not isinstance(value, str) or HASH_PATTERN.fullmatch(value) is None
            for value in hashes.values()
        ):
            raise ChangePlanningError("change plan model hashes are corrupt")
    request_ops: list[Operation] = []
    operation_keys = {"action", "model", "record_type", "id", "expected_revision", "expected_hash", "candidate_revision", "candidate_hash"}
    for row in operations:
        if not isinstance(row, dict) or set(row) != operation_keys:
            raise ChangePlanningError("change plan operation is corrupt")
        if row["action"] not in {"upsert", "delete"} or row["model"] not in MODEL_NAMES:
            raise ChangePlanningError("change plan operation is corrupt")
        if not all(isinstance(row[key], str) for key in ("record_type", "id", "expected_hash", "candidate_hash")):
            raise ChangePlanningError("change plan operation is corrupt")
        for revision in (row["expected_revision"], row["candidate_revision"]):
            if revision is not None and (type(revision) is not int or revision < 0):
                raise ChangePlanningError("change plan revision is corrupt")
        for digest in (row["expected_hash"], row["candidate_hash"]):
            if digest and HASH_PATTERN.fullmatch(digest) is None:
                raise ChangePlanningError("change plan operation hash is corrupt")
        request_ops.append(Operation(row["action"], row["model"], row["record_type"], row["id"], row["expected_revision"], row["expected_hash"], None, row.get("candidate_revision")))
    replacements: list[Replacement] = []
    identities: set[str] = set()
    for row in replacement_rows:
        if not isinstance(row, dict) or set(row) != {"identity", "before_hash", "after_hash"}:
            raise ChangePlanningError("change plan replacement is corrupt")
        identity = row.get("identity")
        identity_path = PurePosixPath(identity) if isinstance(identity, str) else PurePosixPath("/")
        if (
            not isinstance(identity, str)
            or identity in identities
            or identity_path.is_absolute()
            or any(part in {"", ".", ".."} for part in identity_path.parts)
            or not identity.startswith("_paperops/model/")
        ):
            raise ChangePlanningError("change plan replacement identity is corrupt")
        identities.add(identity)
        for digest in (row.get("before_hash"), row.get("after_hash")):
            if not isinstance(digest, str) or (digest and HASH_PATTERN.fullmatch(digest) is None):
                raise ChangePlanningError("change plan replacement hash is corrupt")
        encoded = payload.get(row["identity"])
        try:
            content = base64.b64decode(encoded, validate=True) if isinstance(encoded, str) else None
        except (ValueError, TypeError) as exc:
            raise ChangePlanningError("change plan payload is corrupt") from exc
        if (raw_hash(content) if content is not None else "") != row["after_hash"]:
            raise ChangePlanningError("change plan payload hash is corrupt")
        replacements.append(Replacement(row["identity"], row["before_hash"], row["after_hash"], content))
    if set(payload) != identities:
        raise ChangePlanningError("change plan payload identities are corrupt")
    return ChangePlan(1, change_id, plan["reason"], tuple(sorted({row["model"] for row in operations})), tuple(request_ops), tuple(replacements), MappingProxyType(dict(base_hashes)), MappingProxyType(dict(candidate_hashes)))
