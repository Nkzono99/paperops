"""Journaled workflow plan application and rollback."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path

from paperops.workflow_v2.mutation import canonical_json, raw_hash, safe_generated_dir, validate_identity


def _read_plan(root: Path, plan_id: str) -> dict:
    if not plan_id.startswith("WPLAN-"):
        raise ValueError("invalid plan id")
    path = safe_generated_dir(root, f".paperops/workflow/plans/{plan_id}") / "plan.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("workflow plan is missing or invalid") from exc
    if set(payload) != {"schema_version", "plan_id", "operation", "replacements"} or payload.get("schema_version") != 1 or payload.get("plan_id") != plan_id or not isinstance(payload.get("operation"), str) or not isinstance(payload.get("replacements"), list):
        raise ValueError("workflow plan identity is invalid")
    digest_payload = {"operation": payload["operation"], "replacements": payload["replacements"]}
    expected = "WPLAN-" + hashlib.sha256(canonical_json(digest_payload).encode()).hexdigest()[:16]
    if expected != plan_id:
        raise ValueError("workflow plan content hash is invalid")
    return payload


def _target(root: Path, identity: str) -> Path:
    validate_identity(identity)
    target = root.joinpath(*identity.split("/"))
    current = root
    for part in identity.split("/")[:-1]:
        current = current / part
        if not current.exists() and identity.startswith("_paperops/model/"):
            current.mkdir(mode=0o700)
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("workflow target path is unsafe")
    if not target.exists():
        return target
    metadata = target.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("workflow target is unsafe")
    return target


def _replace(path: Path, content: bytes, mode: int = 0o600) -> None:
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


def execute_workflow_apply(root: Path, plan_id: str, *, confirmed: bool = False) -> str:
    if not confirmed:
        raise ValueError("workflow apply requires explicit confirmation")
    payload = _read_plan(root, plan_id)
    tx_id = "WTX-" + hashlib.sha256(canonical_json(payload).encode()).hexdigest()[:16]
    state = safe_generated_dir(root, f".paperops/workflow/transactions/{tx_id}")
    lock_path = safe_generated_dir(root, ".paperops/workflow") / "lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        journal_path = state / "journal.json"
        if journal_path.exists():
            journal = json.loads(journal_path.read_text())
            if journal.get("state") == "APPLIED":
                return tx_id
        entries = []
        for row in payload["replacements"]:
            identity = row.get("identity")
            before_hash = row.get("before_hash")
            content = row.get("content")
            if not all(isinstance(value, str) for value in (identity, before_hash, content)):
                raise ValueError("workflow replacement is invalid")
            path = _target(root, identity)
            before = path.read_bytes() if path.exists() else b""
            if (raw_hash(before) if path.exists() else "") != before_hash:
                raise ValueError("workflow plan source drifted")
            mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
            entries.append({"identity": identity, "pre": base64.b64encode(before).decode(), "pre_hash": before_hash, "post_hash": raw_hash(content.encode()), "mode": mode, "created": not path.exists(), "content": content})
        journal = {"schema_version": 1, "transaction_id": tx_id, "plan_id": plan_id, "state": "PREPARED", "entries": entries}
        journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
        journal["state"] = "APPLYING"
        journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
        written = []
        try:
            for entry in entries:
                _replace(_target(root, entry["identity"]), entry["content"].encode(), entry["mode"])
                written.append(entry)
            from paperops.model_validation import run_model_validation

            affected = set()
            for entry in entries:
                identity = entry["identity"]
                if identity.startswith("_paperops/model/issues/"):
                    affected.add("issue")
                elif identity.startswith("_paperops/model/research/"):
                    affected.add("research")
                elif identity.startswith("_paperops/model/manuscript/"):
                    affected.add("manuscript")
                elif identity.startswith("_paperops/model/publication/"):
                    affected.add("publication")
                elif identity.startswith("_paperops/model/editorial/"):
                    affected.update({"editorial", "results_hierarchy"})
            for model in sorted(affected):
                validation = run_model_validation(root, model, strict=True)
                if not validation.ok:
                    raise ValueError(f"post-apply {model} validation failed")
        except BaseException:
            for entry in reversed(written):
                path = _target(root, entry["identity"])
                if entry.get("created"):
                    path.unlink(missing_ok=True)
                else:
                    _replace(path, base64.b64decode(entry["pre"]), entry["mode"])
            journal["state"] = "ROLLED_BACK"
            journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
            raise
        journal["state"] = "APPLIED"
        for entry in journal["entries"]:
            entry.pop("content", None)
        journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
    return tx_id


def execute_workflow_rollback(root: Path, transaction_id: str, *, confirmed: bool = False) -> str:
    if not confirmed:
        raise ValueError("workflow rollback requires explicit confirmation")
    journal_path = safe_generated_dir(root, f".paperops/workflow/transactions/{transaction_id}") / "journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("transaction_id") != transaction_id or journal.get("state") not in {"APPLIED", "ROLLED_BACK"}:
        raise ValueError("workflow transaction cannot be rolled back")
    if journal["state"] == "ROLLED_BACK":
        return transaction_id
    for entry in journal["entries"]:
        path = _target(root, entry["identity"])
        if raw_hash(path.read_bytes()) != entry["post_hash"]:
            raise ValueError("workflow rollback conflicts with a newer edit")
    for entry in reversed(journal["entries"]):
        path = _target(root, entry["identity"])
        if entry.get("created"):
            path.unlink(missing_ok=True)
        else:
            _replace(path, base64.b64decode(entry["pre"]), entry["mode"])
    journal["state"] = "ROLLED_BACK"
    journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
    return transaction_id


def recover_incomplete_workflow_transactions(root: Path) -> tuple[str, ...]:
    recovered = []
    directory = root / ".paperops/workflow/transactions"
    if not directory.exists():
        return ()
    directory = safe_generated_dir(root, ".paperops/workflow/transactions")
    for journal_path in sorted(directory.glob("WTX-*/journal.json")):
        journal = json.loads(journal_path.read_text())
        if journal.get("state") not in {"PREPARED", "APPLYING"}:
            continue
        for entry in reversed(journal.get("entries", [])):
            path = _target(root, entry["identity"])
            current = raw_hash(path.read_bytes())
            if current == entry["post_hash"]:
                if entry.get("created"):
                    path.unlink(missing_ok=True)
                else:
                    _replace(path, base64.b64decode(entry["pre"]), entry["mode"])
            elif current != entry["pre_hash"]:
                raise ValueError("incomplete workflow transaction conflicts with an edit")
        journal["state"] = "ROLLED_BACK"
        journal_path.write_text(canonical_json(journal, pretty=True), encoding="utf-8")
        recovered.append(journal["transaction_id"])
    return tuple(recovered)
