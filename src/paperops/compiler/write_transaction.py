"""Journaled, conservative application and rollback of validated Writer TeX."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

from .storage import atomic_write_json, semantic_hash
from .types import CompileFinding, _freeze_json, _validate_id
from .writer import build_patch


WRITE_STATES = (
    "planned", "materialized", "validated", "snapshotted", "replacing",
    "committed", "rolled_back", "conflict",
)


class WriteTransactionError(RuntimeError):
    def __init__(self, finding: CompileFinding) -> None:
        super().__init__(finding.message)
        self.finding = finding


class InjectedWriteFailure(RuntimeError):
    pass


class HardCrashSimulation(BaseException):
    """Test-only crash boundary which deliberately bypasses compensation."""


@dataclass(frozen=True)
class WriteTarget:
    identity: str
    pre_hash: str
    post_hash: str
    pre_mode: int
    post_mode: int
    pre_size: int
    post_size: int


@dataclass(frozen=True)
class WriteApplyPlan:
    root: Path
    session_id: str
    transaction_id: str
    sequence: int
    patch_hash: str
    compile_id: str
    compile_bundle_hash: str
    base_manifest_hash: str
    authority: tuple[Mapping[str, Any], ...]
    scope_hash: str
    mirror_impacts: tuple[Mapping[str, Any], ...]
    targets: tuple[WriteTarget, ...]
    confirmed: bool
    no_op: bool = False


@dataclass(frozen=True)
class WriteRollbackPlan:
    root: Path
    session_id: str
    transaction_id: str
    sequence: int
    source_transaction_id: str
    patch_hash: str
    compile_id: str
    compile_bundle_hash: str
    base_manifest_hash: str
    authority: tuple[Mapping[str, Any], ...]
    scope_hash: str
    mirror_impacts: tuple[Mapping[str, Any], ...]
    targets: tuple[WriteTarget, ...]
    confirmed: bool = True
    no_op: bool = False


@dataclass(frozen=True)
class WriteTransactionResult:
    session_id: str
    transaction_id: str
    action: str
    state: str
    no_op: bool = False
    schema_version: int = 1

    @property
    def ok(self) -> bool:
        return self.state == "committed"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "transaction_id": self.transaction_id,
            "action": self.action,
            "state": self.state,
            "no_op": self.no_op,
        }


def _finding(code: str, pointer: str, message: str) -> CompileFinding:
    return CompileFinding(code, pointer, message)


def _fail(code: str, pointer: str, message: str) -> None:
    raise WriteTransactionError(_finding(code, pointer, message))


def _hash_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _safe_identity(identity: str) -> None:
    path = PurePosixPath(identity)
    if (
        not identity.startswith("manuscript/")
        or not identity.endswith(".tex")
        or path.is_absolute()
        or identity != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
        or "\\" in identity
    ):
        _fail("write.transaction_target", "/targets", "write target must be an existing manuscript TeX file")


def _safe_target_path(root: Path, identity: str) -> Path:
    _safe_identity(identity)
    current = root
    for part in PurePosixPath(identity).parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except OSError:
            _fail("write.transaction_target", "/targets", "write target parent is missing or unsafe")
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            _fail("write.transaction_target", "/targets", "write target parent is missing or unsafe")
    return root / identity


def _fingerprint(path: Path) -> tuple[str, int, int]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        _fail("write.transaction_target", "/targets", "write target is missing or unsafe")
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("write.transaction_target", "/targets", "write target must be a single-link regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        content = b"".join(chunks)
        return _hash_bytes(content), stat.S_IMODE(info.st_mode), len(content)
    finally:
        os.close(descriptor)


def _matches(path: Path, digest: str, mode: int, size: int) -> bool:
    try:
        return _fingerprint(path) == (digest, mode, size)
    except WriteTransactionError:
        return False


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _writer_lock(root: Path) -> Iterator[None]:
    state = root / ".paperops/writer"
    state.mkdir(parents=True, exist_ok=True)
    lock = state / ".transaction.lock"
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _next_sequence(root: Path) -> int:
    path = root / ".paperops/writer/.transaction-sequence.json"
    current = 0
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            current = int(value["sequence"])
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            _fail("write.transaction_sequence", "/sequence", "Writer transaction sequence is corrupt")
    sequence = current + 1
    atomic_write_json(path, {"schema_version": 1, "sequence": sequence})
    _fsync_dir(path.parent)
    return sequence


def _transaction_id(sequence: int) -> str:
    return f"write-v1-{sequence:012d}"


def _tx_dir(root: Path, session_id: str, transaction_id: str) -> Path:
    _validate_id(session_id, "Writer session ID")
    _validate_id(transaction_id, "Writer transaction ID")
    return root / ".paperops/writer" / session_id / "transactions" / transaction_id


def _journal_payload(plan: WriteApplyPlan | WriteRollbackPlan, action: str, state: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "session_id": plan.session_id,
        "transaction_id": plan.transaction_id,
        "sequence": plan.sequence,
        "action": action,
        "source_transaction_id": getattr(plan, "source_transaction_id", ""),
        "state": state,
        "patch_hash": plan.patch_hash,
        "compile_id": plan.compile_id,
        "compile_bundle_hash": plan.compile_bundle_hash,
        "base_manifest_hash": plan.base_manifest_hash,
        "authority": [dict(item) for item in plan.authority],
        "scope_hash": plan.scope_hash,
        "human_confirmation": plan.confirmed,
        "mirror_impacts": [dict(item) for item in plan.mirror_impacts],
        "targets": [target.__dict__ for target in plan.targets],
        "snapshot_manifest_hash": _snapshot_manifest_hash(plan.targets, action),
    }


def _write_journal(plan: WriteApplyPlan | WriteRollbackPlan, action: str, state: str) -> None:
    if state not in WRITE_STATES:
        raise ValueError(state)
    directory = _tx_dir(plan.root, plan.session_id, plan.transaction_id)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_json(directory / "journal.json", _journal_payload(plan, action, state))
    _fsync_dir(directory)


def _transition(plan, action: str, state: str, fail_at: str) -> None:
    if fail_at == f"before:{state}":
        raise InjectedWriteFailure(fail_at)
    if fail_at == f"hard-before:{state}":
        raise HardCrashSimulation(fail_at)
    _write_journal(plan, action, state)
    if fail_at == f"after:{state}":
        raise InjectedWriteFailure(fail_at)
    if fail_at == f"hard-after:{state}":
        raise HardCrashSimulation(fail_at)


def _targets_from_patch(rows: object) -> tuple[WriteTarget, ...]:
    if not isinstance(rows, (list, tuple)) or not rows:
        _fail("write.transaction_empty", "/target_files", "validated patch has no TeX targets")
    targets: list[WriteTarget] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            _fail("write.transaction_patch", "/target_files", "validated patch target is malformed")
        identity = str(row.get("identity", ""))
        _safe_identity(identity)
        if identity in seen:
            _fail("write.transaction_patch", "/target_files", "validated patch repeats a target")
        seen.add(identity)
        pre = row.get("preimage")
        post = row.get("candidate")
        if not isinstance(pre, Mapping) or not isinstance(post, Mapping):
            _fail("write.transaction_patch", "/target_files", "validated patch requires pre/post file states")
        if pre.get("identity") != identity or post.get("identity") != identity:
            _fail("write.transaction_patch", "/target_files", "target identity does not match its file states")
        targets.append(
            WriteTarget(
                identity,
                str(pre.get("content_hash", "")),
                str(post.get("content_hash", "")),
                int(pre.get("mode", -1)),
                int(post.get("mode", -1)),
                int(pre.get("size", -1)),
                int(post.get("size", -1)),
            )
        )
    return tuple(sorted(targets, key=lambda item: item.identity))


def _read_journals(root: Path, session_id: str | None = None) -> list[dict[str, Any]]:
    base = root / ".paperops/writer"
    pattern = f"{session_id}/transactions/*/journal.json" if session_id else "*/transactions/*/journal.json"
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob(pattern)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, dict):
            row["_path"] = path
            rows.append(row)
    return rows


def _targets_from_journal(row: Mapping[str, Any]) -> tuple[WriteTarget, ...]:
    try:
        return tuple(WriteTarget(**item) for item in row["targets"])
    except (KeyError, TypeError, ValueError) as error:
        raise WriteTransactionError(
            _finding("write.transaction_journal", "/targets", "Writer transaction journal is malformed")
        ) from error


def _find_committed_apply(root: Path, session_id: str, patch_hash: str) -> Mapping[str, Any] | None:
    matches = [
        row for row in _read_journals(root, session_id)
        if row.get("action") == "apply" and row.get("state") == "committed"
        and row.get("patch_hash") == patch_hash
    ]
    return max(matches, key=lambda row: int(row.get("sequence", 0))) if matches else None


def plan_write_apply(root: str | Path, session_id: str, *, confirmed: bool = False) -> WriteApplyPlan:
    project = Path(root).expanduser().absolute()
    _validate_id(session_id, "Writer session ID")
    patch_path = project / ".paperops/writer" / session_id / "patch.json"
    try:
        persisted = json.loads(patch_path.read_text(encoding="utf-8"))
        patch_hash = str(persisted["patch_hash"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise WriteTransactionError(_finding("write.patch_missing", "/patch", "run write check before apply")) from error
    with _writer_lock(project):
        previous = _find_committed_apply(project, session_id, patch_hash)
        if previous is not None:
            targets = _targets_from_journal(previous)
            if all(_matches(project / item.identity, item.post_hash, item.post_mode, item.post_size) for item in targets):
                return WriteApplyPlan(
                    project, session_id, str(previous["transaction_id"]), int(previous["sequence"]),
                    patch_hash, str(previous["compile_id"]), str(previous["compile_bundle_hash"]),
                    str(previous["base_manifest_hash"]), tuple(_freeze_json(x) for x in previous["authority"]),
                    str(previous["scope_hash"]), tuple(_freeze_json(x) for x in previous["mirror_impacts"]),
                    targets, True, True,
                )
        if not confirmed:
            _fail("write.confirmation_required", "/confirmation", "write apply requires explicit confirmation")
        patch = build_patch(project, session_id)
        if not patch.ok or patch.conservation_result != "passed":
            _fail("write.patch_blocked", "/patch", "Writer patch is not fully validated")
        if not patch.applicable or patch.source_mode != "authoritative":
            _fail("write.shadow_apply", "/source_mode", "shadow compile output cannot be applied")
        if not patch.compile_bundle_hash:
            _fail("write.patch_unbound", "/compile_bundle_hash", "Writer patch is not bound to its compile bundle")
        if persisted != patch.to_dict() or patch_hash != patch.patch_hash:
            _fail("write.patch_changed", "/patch", "Writer patch changed during apply planning")
        targets = _targets_from_patch(patch.target_files)
        for item in targets:
            living = _safe_target_path(project, item.identity)
            if not _matches(living, item.pre_hash, item.pre_mode, item.pre_size):
                _fail("write.base_drift", "/targets", "living TeX changed after patch validation")
            candidate = project / ".paperops/writer" / session_id / "workspace" / item.identity
            if not _matches(candidate, item.post_hash, item.post_mode, item.post_size):
                _fail("write.candidate_drift", "/targets", "Writer candidate changed after patch validation")
        sequence = _next_sequence(project)
        return WriteApplyPlan(
            project, session_id, _transaction_id(sequence), sequence, patch.patch_hash,
            patch.compile_id, patch.compile_bundle_hash, patch.base_manifest_hash,
            patch.authority, semantic_hash(patch.write_scope), patch.mirror_impacts,
            targets, confirmed,
        )


def _snapshot_manifest_hash(targets: tuple[WriteTarget, ...], action: str) -> str:
    side = "pre" if action == "apply" else "post"
    return semantic_hash(
        [{"identity": row.identity, "hash": getattr(row, f"{side}_hash"), "mode": getattr(row, f"{side}_mode"), "size": getattr(row, f"{side}_size")} for row in targets]
    )


def _copy_verified(source: Path, destination: Path, digest: str, mode: int, size: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_descriptor = -1
    destination_descriptor = -1
    try:
        source_descriptor = os.open(
            source,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        info = os.fstat(source_descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != mode
            or info.st_size != size
        ):
            _fail("write.transaction_drift", "/targets", "transaction input changed")
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            mode,
        )
        hasher = hashlib.sha256()
        copied = 0
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            copied += len(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                view = view[written:]
        if "sha256:" + hasher.hexdigest() != digest or copied != size:
            _fail("write.transaction_drift", "/targets", "transaction input changed")
        os.fchmod(destination_descriptor, mode)
        os.fsync(destination_descriptor)
    except OSError as error:
        raise WriteTransactionError(
            _finding("write.transaction_copy", "/targets", "transaction copy failed safely")
        ) from error
    finally:
        if source_descriptor >= 0:
            os.close(source_descriptor)
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
    if not _matches(destination, digest, mode, size):
        _fail("write.transaction_copy", "/targets", "transaction copy verification failed")


def _snapshot(plan, action: str) -> None:
    directory = _tx_dir(plan.root, plan.session_id, plan.transaction_id) / "snapshot"
    side = "pre" if action == "apply" else "post"
    for item in plan.targets:
        _copy_verified(
            plan.root / item.identity,
            directory / item.identity,
            getattr(item, f"{side}_hash"),
            getattr(item, f"{side}_mode"),
            getattr(item, f"{side}_size"),
        )
    atomic_write_json(directory / "manifest.json", {
        "schema_version": 1,
        "manifest_hash": _snapshot_manifest_hash(plan.targets, action),
        "targets": [item.__dict__ for item in plan.targets],
        "side": side,
    })
    _fsync_dir(directory)


def _verify_snapshot(root: Path, session_id: str, transaction_id: str, targets: tuple[WriteTarget, ...], action: str) -> bool:
    directory = _tx_dir(root, session_id, transaction_id) / "snapshot"
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    side = "pre" if action == "apply" else "post"
    if manifest.get("manifest_hash") != _snapshot_manifest_hash(targets, action) or manifest.get("side") != side:
        return False
    return all(
        _matches(directory / item.identity, getattr(item, f"{side}_hash"), getattr(item, f"{side}_mode"), getattr(item, f"{side}_size"))
        for item in targets
    )


def _replace_from(source: Path, target: Path, digest: str, mode: int, size: int, transaction_id: str) -> None:
    temporary = target.with_name(f".{target.name}.{transaction_id}.tmp")
    temporary.unlink(missing_ok=True)
    try:
        _copy_verified(source, temporary, digest, mode, size)
        os.replace(temporary, target)
        _fsync_dir(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _restore(plan, action: str) -> bool:
    if not _verify_snapshot(plan.root, plan.session_id, plan.transaction_id, plan.targets, action):
        return False
    side = "pre" if action == "apply" else "post"
    snapshot = _tx_dir(plan.root, plan.session_id, plan.transaction_id) / "snapshot"
    for item in plan.targets:
        expected_post = item.post_hash if action == "apply" else item.pre_hash
        expected_post_mode = item.post_mode if action == "apply" else item.pre_mode
        expected_post_size = item.post_size if action == "apply" else item.pre_size
        current = plan.root / item.identity
        if _matches(current, getattr(item, f"{side}_hash"), getattr(item, f"{side}_mode"), getattr(item, f"{side}_size")):
            continue
        if not _matches(current, expected_post, expected_post_mode, expected_post_size):
            return False
        _replace_from(snapshot / item.identity, current, getattr(item, f"{side}_hash"), getattr(item, f"{side}_mode"), getattr(item, f"{side}_size"), plan.transaction_id)
    return True


def _execute(plan, action: str, source_side: str, destination_side: str, *, fail_at: str) -> WriteTransactionResult:
    if plan.no_op:
        return WriteTransactionResult(plan.session_id, plan.transaction_id, action, "committed", True)
    with _writer_lock(plan.root):
        reached_replacing = False
        try:
            _transition(plan, action, "planned", fail_at)
            _transition(plan, action, "materialized", fail_at)
            _transition(plan, action, "validated", fail_at)
            _snapshot(plan, action)
            _transition(plan, action, "snapshotted", fail_at)
            _transition(plan, action, "replacing", fail_at)
            reached_replacing = True
            if action == "apply":
                sources = plan.root / ".paperops/writer" / plan.session_id / "workspace"
            else:
                sources = _tx_dir(plan.root, plan.session_id, plan.source_transaction_id) / "snapshot"
            for index, item in enumerate(plan.targets):
                source = sources / item.identity
                _replace_from(
                    source,
                    plan.root / item.identity,
                    getattr(item, f"{destination_side}_hash"),
                    getattr(item, f"{destination_side}_mode"),
                    getattr(item, f"{destination_side}_size"),
                    plan.transaction_id,
                )
                if fail_at == f"after:replace:{index}":
                    raise InjectedWriteFailure(fail_at)
                if fail_at == f"hard-after:replace:{index}":
                    raise HardCrashSimulation(fail_at)
                _write_journal(plan, action, "replacing")
            if not all(
                _matches(plan.root / item.identity, getattr(item, f"{destination_side}_hash"), getattr(item, f"{destination_side}_mode"), getattr(item, f"{destination_side}_size"))
                for item in plan.targets
            ):
                _fail("write.transaction_postcheck", "/targets", "written TeX failed post-write verification")
            _transition(plan, action, "committed", fail_at)
            return WriteTransactionResult(plan.session_id, plan.transaction_id, action, "committed")
        except HardCrashSimulation:
            raise
        except BaseException:
            source_is_intact = all(
                _matches(
                    plan.root / item.identity,
                    getattr(item, f"{source_side}_hash"),
                    getattr(item, f"{source_side}_mode"),
                    getattr(item, f"{source_side}_size"),
                )
                for item in plan.targets
            )
            if (not reached_replacing and source_is_intact) or _restore(plan, action):
                _write_journal(plan, action, "rolled_back")
            else:
                _write_journal(plan, action, "conflict")
            raise


def execute_write_apply(plan: WriteApplyPlan, *, fail_at: str = "") -> WriteTransactionResult:
    return _execute(plan, "apply", "pre", "post", fail_at=fail_at)


def _plan_from_journal(
    root: Path,
    row: Mapping[str, Any],
    *,
    transaction_id: str | None = None,
    sequence: int | None = None,
    action: str | None = None,
    no_op: bool = False,
):
    cls = WriteApplyPlan if (action or row.get("action")) == "apply" else WriteRollbackPlan
    common = dict(
        root=root,
        session_id=str(row["session_id"]),
        transaction_id=transaction_id or str(row["transaction_id"]),
        sequence=sequence if sequence is not None else int(row["sequence"]),
        patch_hash=str(row["patch_hash"]),
        compile_id=str(row["compile_id"]),
        compile_bundle_hash=str(row["compile_bundle_hash"]),
        base_manifest_hash=str(row["base_manifest_hash"]),
        authority=tuple(_freeze_json(x) for x in row["authority"]),
        scope_hash=str(row["scope_hash"]),
        mirror_impacts=tuple(_freeze_json(x) for x in row["mirror_impacts"]),
        targets=_targets_from_journal(row),
        confirmed=bool(row.get("human_confirmation", True)),
        no_op=no_op,
    )
    if cls is WriteRollbackPlan:
        common["source_transaction_id"] = str(row.get("source_transaction_id") or row["transaction_id"])
    return cls(**common)


def recover_incomplete_writes(root: str | Path) -> tuple[CompileFinding, ...]:
    project = Path(root).expanduser().absolute()
    findings: list[CompileFinding] = []
    with _writer_lock(project):
        for row in _read_journals(project):
            state = row.get("state")
            if state in {"committed", "rolled_back", "conflict"}:
                continue
            try:
                plan = _plan_from_journal(project, row)
                action = str(row.get("action"))
                if state in {"planned", "materialized", "validated", "snapshotted"}:
                    if all(_matches(project / item.identity, item.pre_hash if action == "apply" else item.post_hash, item.pre_mode if action == "apply" else item.post_mode, item.pre_size if action == "apply" else item.post_size) for item in plan.targets):
                        _write_journal(plan, action, "rolled_back")
                        continue
                if _restore(plan, action):
                    _write_journal(plan, action, "rolled_back")
                else:
                    _write_journal(plan, action, "conflict")
                    findings.append(_finding("write.recovery_conflict", "/transactions", "incomplete Writer transaction conflicts with living TeX"))
            except (KeyError, TypeError, ValueError, WriteTransactionError):
                path = row.get("_path")
                if isinstance(path, Path):
                    row.pop("_path", None)
                    row["state"] = "conflict"
                    atomic_write_json(path, row)
                findings.append(_finding("write.recovery_conflict", "/transactions", "Writer transaction journal or snapshot is invalid"))
    return tuple(findings)


def plan_write_rollback(root: str | Path, transaction_id: str = "") -> WriteRollbackPlan:
    project = Path(root).expanduser().absolute()
    with _writer_lock(project):
        applies = [row for row in _read_journals(project) if row.get("action") == "apply" and row.get("state") == "committed"]
        if transaction_id:
            applies = [row for row in applies if row.get("transaction_id") == transaction_id]
        if not applies:
            _fail("write.rollback_missing", "/transaction", "committed Writer apply transaction was not found")
        source = max(applies, key=lambda row: int(row.get("sequence", 0)))
        source_targets = _targets_from_journal(source)
        rollbacks = [row for row in _read_journals(project) if row.get("action") == "rollback" and row.get("source_transaction_id") == source.get("transaction_id") and row.get("state") == "committed"]
        if rollbacks and all(_matches(project / item.identity, item.pre_hash, item.pre_mode, item.pre_size) for item in source_targets):
            latest = max(rollbacks, key=lambda row: int(row.get("sequence", 0)))
            return _plan_from_journal(project, latest, no_op=True)
        newer = [row for row in _read_journals(project) if row.get("action") == "apply" and row.get("state") == "committed" and int(row.get("sequence", 0)) > int(source.get("sequence", 0))]
        if any({item.identity for item in _targets_from_journal(row)} & {item.identity for item in source_targets} for row in newer):
            _fail("write.rollback_not_head", "/transaction", "an older overlapping Writer apply cannot be rolled back")
        if not all(_matches(project / item.identity, item.post_hash, item.post_mode, item.post_size) for item in source_targets):
            _fail("write.rollback_conflict", "/targets", "living TeX was edited after Writer apply")
        if not _verify_snapshot(project, str(source["session_id"]), str(source["transaction_id"]), source_targets, "apply"):
            _fail("write.rollback_snapshot", "/snapshot", "Writer apply snapshot is missing or corrupt")
        sequence = _next_sequence(project)
        return WriteRollbackPlan(
            project, str(source["session_id"]), _transaction_id(sequence), sequence,
            str(source["transaction_id"]), str(source["patch_hash"]), str(source["compile_id"]),
            str(source["compile_bundle_hash"]), str(source["base_manifest_hash"]),
            tuple(_freeze_json(x) for x in source["authority"]), str(source["scope_hash"]),
            tuple(_freeze_json(x) for x in source["mirror_impacts"]), source_targets,
        )


def execute_write_rollback(plan: WriteRollbackPlan, *, fail_at: str = "") -> WriteTransactionResult:
    return _execute(plan, "rollback", "post", "pre", fail_at=fail_at)


__all__ = [
    "HardCrashSimulation", "InjectedWriteFailure", "WRITE_STATES", "WriteApplyPlan",
    "WriteRollbackPlan", "WriteTarget", "WriteTransactionError", "WriteTransactionResult",
    "execute_write_apply", "execute_write_rollback", "plan_write_apply",
    "plan_write_rollback", "recover_incomplete_writes",
]
