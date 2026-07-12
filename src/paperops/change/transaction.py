"""Durable multi-model application, crash recovery, and rollback."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from paperops.cli.manifest import as_table, dumps_manifest_toml, read_manifest
from paperops.model_state import MODEL_NAMES, read_model_states
from paperops.model_validation import run_model_validation
from paperops.workflow_v2.mutation import canonical_json, raw_hash

from .planning import ChangePlanningError, read_change_plan
from .types import Replacement


class ChangeTransactionError(RuntimeError):
    pass


def _transaction_dir(root: Path, transaction_id: str) -> Path:
    current = root
    for name in (".paperops", "changes", "transactions", transaction_id):
        current /= name
        if not current.exists():
            current.mkdir(mode=0o700)
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


def recover_incomplete_changes(root: Path) -> tuple[str, ...]:
    root = root.expanduser().resolve()
    directory = root / ".paperops/changes/transactions"
    if not directory.exists():
        return ()
    recovered = []
    for journal_path in sorted(directory.glob("CTX-*/journal.json")):
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ChangeTransactionError("incomplete change journal is corrupt") from exc
        if journal.get("state") not in {"PREPARED", "APPLYING"}:
            continue
        for entry in reversed(journal.get("entries", [])):
            current = _hash(_target(root, entry["identity"], create_parents=False))
            if current == entry["post_hash"]:
                _restore_entry(root, entry)
            elif current != entry["pre_hash"]:
                raise ChangeTransactionError("incomplete change conflicts with a manual edit")
        journal["state"] = "ROLLED_BACK"
        _write_journal(journal_path, journal)
        recovered.append(journal["transaction_id"])
    return tuple(recovered)


def apply_change(root: Path, change_id: str, *, confirmed: bool = False, fail_after: int | None = None) -> str:
    if not confirmed:
        raise ChangeTransactionError("change apply requires explicit confirmation")
    root = root.expanduser().resolve()
    try:
        plan = read_change_plan(root, change_id)
    except ChangePlanningError as exc:
        raise ChangeTransactionError(str(exc)) from exc
    transaction_id = "CTX-" + hashlib.sha256(change_id.encode()).hexdigest()[:20]
    state = _transaction_dir(root, transaction_id)
    lock_path = root / ".paperops/changes/lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        recover_incomplete_changes(root)
        journal_path = state / "journal.json"
        if journal_path.exists():
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
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
        written: list[dict[str, Any]] = []
        try:
            for index, entry in enumerate(entries, start=1):
                _apply_entry(root, entry); written.append(entry)
                if fail_after == index:
                    raise RuntimeError("injected change transaction failure")
            result = run_model_validation(root, "all", strict=False)
            if not result.ok or any(result.hashes.get(name) != plan.candidate_model_hashes[name] for name in MODEL_NAMES):
                raise ChangeTransactionError("post-apply six-model validation failed")
        except BaseException:
            for entry in reversed(written):
                _restore_entry(root, entry)
            journal["state"] = "ROLLED_BACK"; _write_journal(journal_path, journal)
            raise
        journal["state"] = "COMMITTED"
        for entry in journal["entries"]:
            entry.pop("post", None)
        _write_journal(journal_path, journal)
    return transaction_id


def rollback_change(root: Path, transaction_id: str, *, confirmed: bool = False) -> str:
    if not confirmed:
        raise ChangeTransactionError("change rollback requires explicit confirmation")
    root = root.expanduser().resolve()
    if not transaction_id.startswith("CTX-"):
        raise ChangeTransactionError("invalid change transaction id")
    original_path = _transaction_dir(root, transaction_id) / "journal.json"
    try:
        original = json.loads(original_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangeTransactionError("change transaction journal is missing or invalid") from exc
    if original.get("state") != "COMMITTED" or original.get("transaction_id") != transaction_id:
        raise ChangeTransactionError("only committed changes can be rolled back")
    receipt_id = "RBK-" + hashlib.sha256(transaction_id.encode()).hexdigest()[:20]
    receipt_path = _transaction_dir(root, receipt_id) / "journal.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("state") == "COMMITTED" and all(_hash(_target(root, row["identity"])) == row["pre_hash"] for row in original["entries"]):
            return receipt_id
        raise ChangeTransactionError("rollback receipt conflicts with current state")
    for entry in original["entries"]:
        if _hash(_target(root, entry["identity"])) != entry["post_hash"]:
            raise ChangeTransactionError("change rollback conflicts with a newer edit")
    receipt = {"schema_version": 1, "transaction_id": receipt_id, "rollback_of": transaction_id, "state": "APPLYING", "entries": original["entries"]}
    _write_journal(receipt_path, receipt)
    restored: list[dict[str, Any]] = []
    try:
        for entry in reversed(original["entries"]):
            _restore_entry(root, entry); restored.append(entry)
    except BaseException:
        for entry in reversed(restored):
            post = dict(entry)
            plan = read_change_plan(root, original["change_id"])
            content_by_identity = {item.identity: item.content for item in plan.replacements}
            if entry["identity"] == ".pops/manifest.toml":
                raise ChangeTransactionError("rollback compensation requires manual recovery")
            content = content_by_identity[entry["identity"]]
            post["post"] = base64.b64encode(content).decode() if content is not None else None
            _apply_entry(root, post)
        raise
    receipt["state"] = "COMMITTED"; _write_journal(receipt_path, receipt)
    return receipt_id
