"""Durable multi-model application, crash recovery, and rollback."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from paperops.cli.manifest import as_table, dumps_manifest_toml, read_manifest
from paperops.model_state import MODEL_NAMES, read_model_states
from paperops.model_validation import run_model_validation
from paperops.workflow_v2.mutation import canonical_json, raw_hash

from .planning import CHANGE_ID_PATTERN, ChangePlanningError, read_change_plan
from .types import Replacement


class ChangeTransactionError(RuntimeError):
    pass


TRANSACTION_ID_PATTERN = re.compile(r"^CTX-[0-9a-f]{20}$")
ROLLBACK_ID_PATTERN = re.compile(r"^RBK-[0-9a-f]{20}$")
_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def _transaction_dir(root: Path, transaction_id: str, *, create: bool) -> Path:
    pattern = ROLLBACK_ID_PATTERN if transaction_id.startswith("RBK-") else TRANSACTION_ID_PATTERN
    if pattern.fullmatch(transaction_id) is None:
        raise ChangeTransactionError("invalid change transaction id")
    current = root
    for name in (".paperops", "changes", "transactions", transaction_id):
        current /= name
        if not current.exists():
            if not create:
                raise ChangeTransactionError("change transaction journal is missing or invalid")
            current.mkdir(mode=0o700)
            parent = os.open(current.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ChangeTransactionError("change transaction directory is unsafe")
    return current


def _target(root: Path, identity: str, *, create_parents: bool = False) -> Path:
    path = PurePosixPath(identity)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or not (
        identity.startswith("_paperops/model/") or identity == ".pops/manifest.toml"
    ):
        raise ChangeTransactionError("change target identity is unsafe")
    current = root
    for part in path.parts[:-1]:
        current /= part
        if not current.exists():
            if not create_parents:
                raise ChangeTransactionError("change target parent is missing")
            current.mkdir(mode=0o700)
            parent = os.open(current.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ChangeTransactionError("change target parent is unsafe")
    target = root.joinpath(*path.parts)
    if target.exists() or target.is_symlink():
        metadata = target.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ChangeTransactionError("change target must be a regular file")
    return target


def _hash(path: Path) -> str:
    return raw_hash(path.read_bytes()) if path.exists() else ""


def _replace(path: Path, content: bytes, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, content)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _delete(path: Path) -> None:
    path.unlink()
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _write_journal(path: Path, journal: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, canonical_json(journal, pretty=True).encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _decoded(value: object, digest: object, label: str) -> bytes | None:
    if value is None:
        if digest != "":
            raise ChangeTransactionError(f"change journal {label} hash is invalid")
        return None
    if not isinstance(value, str) or not isinstance(digest, str) or _HASH_PATTERN.fullmatch(digest) is None:
        raise ChangeTransactionError(f"change journal {label} is invalid")
    try:
        content = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ChangeTransactionError(f"change journal {label} is invalid") from exc
    if raw_hash(content) != digest:
        raise ChangeTransactionError(f"change journal {label} hash is invalid")
    return content


def _read_journal(path: Path, expected_id: str) -> dict[str, Any]:
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangeTransactionError("change transaction journal is missing or invalid") from exc
    is_rollback = ROLLBACK_ID_PATTERN.fullmatch(expected_id) is not None
    required = {"schema_version", "transaction_id", "state", "entries", "rollback_of" if is_rollback else "change_id"}
    if not isinstance(journal, dict) or set(journal) != required or journal.get("schema_version") != 1 or journal.get("transaction_id") != expected_id:
        raise ChangeTransactionError("change transaction journal identity is invalid")
    state = journal.get("state")
    if state not in {"PREPARED", "APPLYING", "COMMITTED", "ROLLED_BACK"}:
        raise ChangeTransactionError("change transaction journal state is invalid")
    if is_rollback:
        rollback_of = str(journal.get("rollback_of", ""))
        if TRANSACTION_ID_PATTERN.fullmatch(rollback_of) is None:
            raise ChangeTransactionError("rollback journal source is invalid")
        canonical = "RBK-" + hashlib.sha256(rollback_of.encode()).hexdigest()[:20]
    else:
        change_id = str(journal.get("change_id", ""))
        if CHANGE_ID_PATTERN.fullmatch(change_id) is None:
            raise ChangeTransactionError("change journal plan id is invalid")
        canonical = "CTX-" + hashlib.sha256(change_id.encode()).hexdigest()[:20]
    if expected_id != canonical:
        raise ChangeTransactionError("change transaction journal id is not canonical")
    entries = journal.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ChangeTransactionError("change transaction journal entries are invalid")
    identities: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"identity", "pre", "pre_hash", "post", "post_hash", "mode"}:
            raise ChangeTransactionError("change transaction journal entry is invalid")
        identity = entry.get("identity")
        if not isinstance(identity, str) or identity in identities:
            raise ChangeTransactionError("change transaction journal identity is invalid")
        identities.add(identity)
        _target(path.parents[4], identity, create_parents=False)
        _decoded(entry.get("pre"), entry.get("pre_hash"), "preimage")
        _decoded(entry.get("post"), entry.get("post_hash"), "postimage")
        mode = entry.get("mode")
        if type(mode) is not int or mode < 0 or mode > 0o777:
            raise ChangeTransactionError("change transaction journal mode is invalid")
    return journal


@contextmanager
def _change_lock(root: Path):
    changes = root
    for name in (".paperops", "changes"):
        changes /= name
        if changes.is_symlink():
            raise ChangeTransactionError("change lock directory is unsafe")
        if not changes.exists():
            changes.mkdir(mode=0o700)
            parent = os.open(changes.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        metadata = changes.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ChangeTransactionError("change lock directory is unsafe")
    lock_path = changes / "lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _future_manifest(root: Path, hashes: dict[str, str]) -> bytes:
    manifest = read_manifest(root / ".pops/manifest.toml")
    models = as_table(manifest.get("models"))
    for name in MODEL_NAMES:
        row = as_table(models.get(name))
        row["current_hash"] = hashes[name]
        models[name] = row
    merged = dict(manifest); merged["models"] = models
    return dumps_manifest_toml(merged).encode("utf-8")


def _entries(root: Path, replacements: tuple[Replacement, ...]) -> list[dict[str, Any]]:
    entries = []
    for replacement in sorted(replacements, key=lambda item: item.identity):
        path = _target(root, replacement.identity, create_parents=replacement.content is not None)
        before = path.read_bytes() if path.exists() else None
        if (raw_hash(before) if before is not None else "") != replacement.before_hash:
            raise ChangeTransactionError(f"change source drifted: {replacement.identity}")
        entries.append({
            "identity": replacement.identity,
            "pre": base64.b64encode(before).decode() if before is not None else None,
            "pre_hash": replacement.before_hash,
            "post_hash": replacement.after_hash,
            "post": base64.b64encode(replacement.content).decode() if replacement.content is not None else None,
            "mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600,
        })
    return entries


def _restore_entry(root: Path, entry: dict[str, Any]) -> None:
    path = _target(root, entry["identity"], create_parents=entry["pre"] is not None)
    if entry["pre"] is None:
        if path.exists():
            _delete(path)
    else:
        _replace(path, base64.b64decode(entry["pre"], validate=True), int(entry["mode"]))


def _apply_entry(root: Path, entry: dict[str, Any]) -> None:
    path = _target(root, entry["identity"], create_parents=entry["post"] is not None)
    if entry["post"] is None:
        if not path.exists():
            raise ChangeTransactionError("planned delete target disappeared")
        _delete(path)
    else:
        _replace(path, base64.b64decode(entry["post"], validate=True), int(entry["mode"]))


def _recover_incomplete_changes_locked(root: Path) -> tuple[str, ...]:
    directory = root / ".paperops/changes/transactions"
    if not directory.exists():
        return ()
    recovered = []
    for journal_path in sorted(directory.glob("*-*/journal.json")):
        transaction_id = journal_path.parent.name
        if TRANSACTION_ID_PATTERN.fullmatch(transaction_id) is None and ROLLBACK_ID_PATTERN.fullmatch(transaction_id) is None:
            continue
        checked_path = _transaction_dir(root, transaction_id, create=False) / "journal.json"
        journal = _read_journal(checked_path, transaction_id)
        if journal.get("state") not in {"PREPARED", "APPLYING"}:
            continue
        for entry in reversed(journal.get("entries", [])):
            current = _hash(_target(root, entry["identity"], create_parents=False))
            if current == entry["post_hash"]:
                _restore_entry(root, entry)
            elif current != entry["pre_hash"]:
                raise ChangeTransactionError("incomplete change conflicts with a manual edit")
        journal["state"] = "COMMITTED" if transaction_id.startswith("RBK-") else "ROLLED_BACK"
        _write_journal(journal_path, journal)
        recovered.append(journal["transaction_id"])
    return tuple(recovered)


def recover_incomplete_changes(root: Path) -> tuple[str, ...]:
    root = root.expanduser().resolve()
    with _change_lock(root):
        return _recover_incomplete_changes_locked(root)


def apply_change(root: Path, change_id: str, *, confirmed: bool = False, fail_after: int | None = None) -> str:
    if not confirmed:
        raise ChangeTransactionError("change apply requires explicit confirmation")
    root = root.expanduser().resolve()
    try:
        plan = read_change_plan(root, change_id)
    except ChangePlanningError as exc:
        raise ChangeTransactionError(str(exc)) from exc
    transaction_id = "CTX-" + hashlib.sha256(change_id.encode()).hexdigest()[:20]
    with _change_lock(root):
        _recover_incomplete_changes_locked(root)
        state = _transaction_dir(root, transaction_id, create=True)
        journal_path = state / "journal.json"
        if journal_path.exists():
            journal = _read_journal(journal_path, transaction_id)
            if journal.get("state") == "COMMITTED":
                if all(_hash(_target(root, row["identity"])) == row["post_hash"] for row in journal["entries"]):
                    return transaction_id
                raise ChangeTransactionError("committed change conflicts with a newer edit")
        states = read_model_states(root)
        validation = run_model_validation(root, "all", strict=False)
        if not validation.ok or any(states[name].current_hash != plan.base_model_hashes[name] or validation.hashes.get(name) != plan.base_model_hashes[name] for name in MODEL_NAMES):
            raise ChangeTransactionError("change plan base authority drifted")
        manifest_path = root / ".pops/manifest.toml"
        manifest_content = _future_manifest(root, dict(plan.candidate_model_hashes))
        replacements = (*plan.replacements, Replacement(".pops/manifest.toml", raw_hash(manifest_path.read_bytes()), raw_hash(manifest_content), manifest_content))
        entries = _entries(root, replacements)
        journal = {"schema_version": 1, "transaction_id": transaction_id, "change_id": change_id, "state": "PREPARED", "entries": entries}
        _write_journal(journal_path, journal)
        journal["state"] = "APPLYING"; _write_journal(journal_path, journal)
        try:
            for index, entry in enumerate(entries, start=1):
                _apply_entry(root, entry)
                if fail_after == index:
                    raise RuntimeError("injected change transaction failure")
            result = run_model_validation(root, "all", strict=False)
            new_warnings = {
                (finding.code, finding.pointer)
                for finding in result.findings
                if finding.severity == "warning"
            } - {
                (finding.code, finding.pointer)
                for finding in validation.findings
                if finding.severity == "warning"
            }
            if not result.ok or new_warnings or any(result.hashes.get(name) != plan.candidate_model_hashes[name] for name in MODEL_NAMES):
                if new_warnings:
                    raise ChangeTransactionError("post-apply validation introduced a new warning")
                raise ChangeTransactionError("post-apply six-model validation failed")
        except BaseException:
            for entry in reversed(journal["entries"]):
                current = _hash(_target(root, entry["identity"], create_parents=False))
                if current == entry["post_hash"]:
                    _restore_entry(root, entry)
                elif current != entry["pre_hash"]:
                    raise ChangeTransactionError("failed change conflicts with a manual edit")
            journal["state"] = "ROLLED_BACK"
            _write_journal(journal_path, journal)
            raise
        journal["state"] = "COMMITTED"
        _write_journal(journal_path, journal)
    return transaction_id


def rollback_change(root: Path, transaction_id: str, *, confirmed: bool = False, fail_after: int | None = None) -> str:
    if not confirmed:
        raise ChangeTransactionError("change rollback requires explicit confirmation")
    root = root.expanduser().resolve()
    if TRANSACTION_ID_PATTERN.fullmatch(transaction_id) is None:
        raise ChangeTransactionError("invalid change transaction id")
    receipt_id = "RBK-" + hashlib.sha256(transaction_id.encode()).hexdigest()[:20]
    with _change_lock(root):
        _recover_incomplete_changes_locked(root)
        original_path = _transaction_dir(root, transaction_id, create=False) / "journal.json"
        original = _read_journal(original_path, transaction_id)
        if original.get("state") != "COMMITTED":
            raise ChangeTransactionError("only committed changes can be rolled back")
        receipt_directory = _transaction_dir(root, receipt_id, create=True)
        receipt_path = receipt_directory / "journal.json"
        if receipt_path.exists():
            receipt = _read_journal(receipt_path, receipt_id)
            if receipt.get("state") == "COMMITTED" and all(_hash(_target(root, row["identity"])) == row["pre_hash"] for row in original["entries"]):
                return receipt_id
            raise ChangeTransactionError("rollback receipt conflicts with current state")
        for entry in original["entries"]:
            if _hash(_target(root, entry["identity"])) != entry["post_hash"]:
                raise ChangeTransactionError("change rollback conflicts with a newer edit")
        receipt = {"schema_version": 1, "transaction_id": receipt_id, "rollback_of": transaction_id, "state": "PREPARED", "entries": original["entries"]}
        _write_journal(receipt_path, receipt)
        receipt["state"] = "APPLYING"
        _write_journal(receipt_path, receipt)
        try:
            for index, entry in enumerate(reversed(original["entries"]), start=1):
                _restore_entry(root, entry)
                if fail_after == index:
                    raise RuntimeError("injected rollback transaction failure")
        except BaseException:
            for entry in reversed(receipt["entries"]):
                current = _hash(_target(root, entry["identity"], create_parents=False))
                if current == entry["post_hash"]:
                    _restore_entry(root, entry)
                elif current != entry["pre_hash"]:
                    raise ChangeTransactionError("incomplete rollback conflicts with a manual edit")
            receipt["state"] = "COMMITTED"
            _write_journal(receipt_path, receipt)
            raise
        receipt["state"] = "COMMITTED"
        _write_journal(receipt_path, receipt)
    return receipt_id


def change_status(root: Path, change_id: str) -> tuple[str, str]:
    if CHANGE_ID_PATTERN.fullmatch(change_id) is None:
        raise ChangeTransactionError("invalid change id")
    root = root.expanduser().resolve()
    transaction_id = "CTX-" + hashlib.sha256(change_id.encode()).hexdigest()[:20]
    transaction_dir = root / ".paperops/changes/transactions" / transaction_id
    if not transaction_dir.exists():
        return "PLANNED", transaction_id
    journal = _read_journal(_transaction_dir(root, transaction_id, create=False) / "journal.json", transaction_id)
    receipt_id = "RBK-" + hashlib.sha256(transaction_id.encode()).hexdigest()[:20]
    receipt_dir = root / ".paperops/changes/transactions" / receipt_id
    if receipt_dir.exists():
        receipt = _read_journal(_transaction_dir(root, receipt_id, create=False) / "journal.json", receipt_id)
        if receipt["state"] == "COMMITTED":
            return "ROLLED_BACK", transaction_id
    return str(journal["state"]), transaction_id
