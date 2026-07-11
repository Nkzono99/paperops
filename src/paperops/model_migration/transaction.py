"""Durable adoption journal and conservative crash recovery."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import stat
import tempfile
from datetime import UTC, datetime
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from paperops.model_state import ModelAuthorityState, read_model_states, write_model_states
from paperops.model_validation import run_model_validation

from .staging import new_transaction_id, snapshot_paths, transaction_paths, verify_snapshot
from .types import MigrationFinding


JOURNAL_STATES = (
    "planned",
    "materialized",
    "validated",
    "snapshotted",
    "replacing",
    "committed",
    "rolled_back",
    "conflict",
)
MODEL_DEPENDENCIES = {
    "research": (),
    "editorial": ("research",),
    "results_hierarchy": ("research",),
    "manuscript": ("research", "editorial", "results_hierarchy"),
    "issue": ("research", "manuscript"),
    "publication": (
        "research",
        "editorial",
        "results_hierarchy",
        "manuscript",
        "issue",
    ),
}
_TARGETS = {
    "research": "_paperops/model/research",
    "editorial": "_paperops/model/editorial",
    "results_hierarchy": "_paperops/model/editorial",
    "manuscript": "_paperops/model/manuscript",
    "issue": "_paperops/model/issues",
    "publication": "_paperops/model/publication/publication-model.yml",
}
_HASH_DOCUMENTS = {
    "research": "_paperops/model/research/index.yml",
    "editorial": "_paperops/model/editorial/editorial-model.yml",
    "results_hierarchy": "_paperops/model/editorial/results-hierarchy.yml",
    "manuscript": "_paperops/model/manuscript/index.yml",
    "issue": "_paperops/model/issues/index.yml",
    "publication": "_paperops/model/publication/publication-model.yml",
}


class TransactionError(RuntimeError):
    def __init__(self, finding: MigrationFinding) -> None:
        super().__init__(finding.message)
        self.finding = finding


class InjectedTransactionFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class TransactionTarget:
    relative_path: str
    old_exists: bool
    old_hash: str
    candidate_hash: str


@dataclass(frozen=True)
class AdoptionPlan:
    root: Path
    model_name: str
    transaction_id: str
    models: tuple[str, ...]
    targets: tuple[TransactionTarget, ...]
    state_hashes: dict[str, str]
    manifest_existed: bool
    manifest_hash: str
    manifest_candidate_hash: str
    no_op: bool = False


@dataclass(frozen=True)
class TransactionJournal:
    schema_version: int
    transaction_id: str
    action: str
    model_name: str
    models: tuple[str, ...]
    state: str
    targets: tuple[TransactionTarget, ...]
    state_hashes: dict[str, str]
    manifest_existed: bool
    manifest_hash: str
    manifest_candidate_hash: str


@dataclass(frozen=True)
class RollbackPlan:
    root: Path
    model_name: str
    transaction_id: str
    models: tuple[str, ...]
    targets: tuple[TransactionTarget, ...]
    restore_transactions: dict[str, str]
    result_states: dict[str, ModelAuthorityState]
    manifest_existed: bool
    manifest_hash: str
    manifest_candidate_hash: str
    no_op: bool = False


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _path_hash(path: Path) -> str:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise TransactionError(
            MigrationFinding("transaction.symlink", f"/{path.name}", "transaction target must not be a symlink")
        )
    if stat.S_ISREG(metadata.st_mode):
        return _file_hash(path)
    if not stat.S_ISDIR(metadata.st_mode):
        raise TransactionError(
            MigrationFinding("transaction.special_file", f"/{path.name}", "transaction target must be a file or directory")
        )
    digest = hashlib.sha256()
    for child in sorted(path.rglob("*")):
        child_metadata = child.lstat()
        if stat.S_ISLNK(child_metadata.st_mode):
            raise TransactionError(
                MigrationFinding("transaction.symlink", "/targets", "transaction tree contains a symlink")
            )
        if child.is_dir():
            continue
        if not stat.S_ISREG(child_metadata.st_mode):
            raise TransactionError(
                MigrationFinding("transaction.special_file", "/targets", "transaction tree contains a special file")
            )
        digest.update(child.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(f"{stat.S_IMODE(child_metadata.st_mode):04o}".encode())
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _manifest_identity(root: Path) -> tuple[bool, str]:
    path = root / ".pops/manifest.toml"
    return (True, _file_hash(path)) if path.is_file() else (False, "")


def _affected(model_name: str) -> tuple[str, ...]:
    return (
        ("editorial", "results_hierarchy")
        if model_name in {"editorial", "results_hierarchy"}
        else (model_name,)
    )


def _read_report(root: Path, transaction_id: str) -> dict[str, Any]:
    path = root / ".paperops/migrations" / transaction_id / "report.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TransactionError(
            MigrationFinding("transaction.report", "/report.json", f"shadow report cannot be read: {error}")
        ) from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise TransactionError(
            MigrationFinding("transaction.report", "/report.json", "shadow report schema is unsupported")
        )
    return payload


def _verify_report_inputs(root: Path, transaction_id: str, report: dict[str, Any]) -> None:
    errors = [item for item in report.get("findings", []) if isinstance(item, dict) and item.get("severity") == "error"]
    if errors:
        raise TransactionError(
            MigrationFinding("transaction.report_blocked", "/findings", "shadow report contains blocking findings")
        )
    checked_sources: set[tuple[str, str]] = set()
    for item in report.get("inventory", []):
        if not isinstance(item, dict):
            continue
        relative = item.get("source_path")
        expected = item.get("source_hash")
        if not isinstance(relative, str) or not isinstance(expected, str) or (relative, expected) in checked_sources:
            continue
        checked_sources.add((relative, expected))
        path = root / relative
        if not path.is_file() or _file_hash(path) != expected:
            raise TransactionError(
                MigrationFinding("migration.source_changed", f"/{relative}", "legacy source changed after shadow generation")
            )
    candidate_root = root / ".paperops/migrations" / transaction_id / "candidate"
    for item in report.get("candidates", []):
        if not isinstance(item, dict):
            continue
        relative = item.get("relative_path")
        expected = item.get("content_hash")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise TransactionError(
                MigrationFinding("transaction.report", "/candidates", "candidate byte hash is missing")
            )
        path = candidate_root / relative
        if not path.is_file() or _file_hash(path) != expected:
            raise TransactionError(
                MigrationFinding("migration.candidate_changed", f"/{relative}", "shadow candidate changed after validation")
            )


def _validate_shadow(root: Path, transaction_id: str, models: tuple[str, ...]) -> None:
    with tempfile.TemporaryDirectory(prefix="pops-adopt-validate-") as tmp:
        target = Path(tmp) / "project"
        shutil.copytree(
            root,
            target,
            ignore=shutil.ignore_patterns(".git", ".paperops", "__pycache__", "*.pyc"),
        )
        candidate_root = root / ".paperops/migrations" / transaction_id / "candidate"
        for relative in dict.fromkeys(_TARGETS[name] for name in models):
            tracked = target / relative
            if tracked.is_dir():
                shutil.rmtree(tracked)
            elif tracked.exists() or tracked.is_symlink():
                tracked.unlink()
            source = candidate_root / relative
            tracked.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, tracked)
            else:
                shutil.copy2(source, tracked)
        for name in models:
            validation = run_model_validation(target, name, strict=True)
            if not validation.ok:
                first = validation.findings[0] if validation.findings else None
                raise TransactionError(
                    MigrationFinding(
                        first.code if first else "transaction.validation",
                        first.pointer if first else "/candidate",
                        first.message if first else "shadow candidate validation failed",
                        first.severity if first else "error",
                    )
                )


def _future_manifest_hash(
    root: Path,
    states: dict[str, ModelAuthorityState],
) -> str:
    with tempfile.TemporaryDirectory(prefix="pops-manifest-") as tmp:
        target = Path(tmp)
        source_manifest = root / ".pops/manifest.toml"
        if source_manifest.is_file():
            (target / ".pops").mkdir()
            shutil.copy2(source_manifest, target / ".pops/manifest.toml")
        write_model_states(target, states)
        return _file_hash(target / ".pops/manifest.toml")
def plan_adoption(root: Path, model_name: str) -> AdoptionPlan:
    project = root.absolute()
    states = read_model_states(project)
    state = states[model_name]
    if state.mode == "v2-authoritative" and state.last_adopt_transaction:
        journal_path = transaction_paths(project, state.last_adopt_transaction).journal_path
        try:
            journal = _read_journal(journal_path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise TransactionError(
                MigrationFinding("state.inconsistent", f"/models/{model_name}", f"committed journal cannot be verified: {error}")
            ) from error
        if journal.state != "committed":
            raise TransactionError(
                MigrationFinding("state.inconsistent", f"/models/{model_name}", "v2 authority does not point to a committed journal")
            )
        for target in journal.targets:
            current = project / target.relative_path
            if not current.exists() or _path_hash(current) != target.candidate_hash:
                raise TransactionError(
                    MigrationFinding("transaction.target_changed", f"/{target.relative_path}", "adopted target changed after commit")
                )
        existed, digest = _manifest_identity(project)
        if not existed or digest != journal.manifest_candidate_hash:
            raise TransactionError(
                MigrationFinding("state.inconsistent", f"/models/{model_name}", "manifest changed after committed adoption")
            )
        return AdoptionPlan(project, model_name, state.last_adopt_transaction, _affected(model_name), (), journal.state_hashes, existed, digest, digest, True)
    if state.mode != "shadow-compare" or not state.last_shadow_transaction:
        raise TransactionError(
            MigrationFinding("transaction.shadow_missing", f"/models/{model_name}", "run `pops model diff` before adoption")
        )
    blockers = [name for name in MODEL_DEPENDENCIES[model_name] if states[name].mode != "v2-authoritative"]
    if blockers:
        raise TransactionError(
            MigrationFinding("transaction.dependency", f"/models/{model_name}", "adoption requires v2 dependencies: " + ", ".join(blockers))
        )
    transaction_id = state.last_shadow_transaction
    report = _read_report(project, transaction_id)
    _verify_report_inputs(project, transaction_id, report)
    models = _affected(model_name)
    _validate_shadow(project, transaction_id, models)
    target_relatives = tuple(dict.fromkeys(_TARGETS[name] for name in models))
    candidate_root = project / ".paperops/migrations" / transaction_id / "candidate"
    targets: list[TransactionTarget] = []
    for relative in target_relatives:
        current = project / relative
        candidate = candidate_root / relative
        if not candidate.exists():
            raise TransactionError(
                MigrationFinding("transaction.candidate_missing", f"/{relative}", "candidate target is missing")
            )
        targets.append(
            TransactionTarget(
                relative,
                current.exists(),
                _path_hash(current) if current.exists() else "",
                _path_hash(candidate),
            )
        )
    candidates = {
        item.get("relative_path"): item.get("semantic_hash")
        for item in report.get("candidates", [])
        if isinstance(item, dict)
    }
    state_hashes: dict[str, str] = {}
    for name in models:
        digest = candidates.get(_HASH_DOCUMENTS[name])
        if not isinstance(digest, str):
            raise TransactionError(
                MigrationFinding("transaction.report", f"/{name}", "model semantic hash is missing from report")
            )
        state_hashes[name] = digest
    manifest_existed, manifest_hash = _manifest_identity(project)
    future_states = dict(states)
    for name in models:
        future_states[name] = replace(
            future_states[name],
            mode="v2-authoritative",
            current_hash=state_hashes[name],
            last_adopt_transaction=transaction_id,
        )
    manifest_candidate_hash = _future_manifest_hash(project, future_states)
    return AdoptionPlan(project, model_name, transaction_id, models, tuple(targets), state_hashes, manifest_existed, manifest_hash, manifest_candidate_hash)


def _journal_from_plan(plan: AdoptionPlan, state: str) -> TransactionJournal:
    return TransactionJournal(1, plan.transaction_id, "adopt", plan.model_name, plan.models, state, plan.targets, plan.state_hashes, plan.manifest_existed, plan.manifest_hash, plan.manifest_candidate_hash)


def _write_journal(root: Path, journal: TransactionJournal) -> None:
    if journal.state not in JOURNAL_STATES:
        raise ValueError(journal.state)
    path = transaction_paths(root, journal.transaction_id).journal_path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": journal.schema_version,
        "transaction_id": journal.transaction_id,
        "action": journal.action,
        "model_name": journal.model_name,
        "models": list(journal.models),
        "state": journal.state,
        "targets": [target.__dict__ for target in journal.targets],
        "state_hashes": journal.state_hashes,
        "manifest_existed": journal.manifest_existed,
        "manifest_hash": journal.manifest_hash,
        "manifest_candidate_hash": journal.manifest_candidate_hash,
    }
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _transition(plan: AdoptionPlan, state: str, fail_at: str) -> None:
    if fail_at == f"before:{state}":
        raise InjectedTransactionFailure(fail_at)
    _write_journal(plan.root, _journal_from_plan(plan, state))
    if fail_at == f"after:{state}":
        raise InjectedTransactionFailure(fail_at)


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def execute_adoption(plan: AdoptionPlan, *, fail_at: str = "") -> TransactionJournal:
    if plan.no_op:
        return _journal_from_plan(plan, "committed")
    _transition(plan, "planned", fail_at)
    _transition(plan, "materialized", fail_at)
    _transition(plan, "validated", fail_at)
    snapshot_inputs = [Path(item.relative_path) for item in plan.targets if item.old_exists]
    if plan.manifest_existed:
        snapshot_inputs.append(Path(".pops/manifest.toml"))
    snapshot_paths(plan.root, plan.transaction_id, tuple(snapshot_inputs))
    _transition(plan, "snapshotted", fail_at)
    _transition(plan, "replacing", fail_at)
    paths = transaction_paths(plan.root, plan.transaction_id)
    for target in plan.targets:
        current = plan.root / target.relative_path
        candidate = paths.candidate_dir / target.relative_path
        replacement = paths.migration_dir / "replacement" / target.relative_path
        replacement.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_dir():
            shutil.copytree(candidate, replacement, copy_function=shutil.copy2)
        else:
            shutil.copy2(candidate, replacement)
        displaced = paths.migration_dir / "displaced" / target.relative_path
        displaced.parent.mkdir(parents=True, exist_ok=True)
        if current.exists() or current.is_symlink():
            os.replace(current, displaced)
        current.parent.mkdir(parents=True, exist_ok=True)
        os.replace(replacement, current)
    if fail_at == "after:targets_replaced":
        raise InjectedTransactionFailure(fail_at)
    states = read_model_states(plan.root)
    for name in plan.models:
        states[name] = replace(
            states[name],
            mode="v2-authoritative",
            current_hash=plan.state_hashes[name],
            last_adopt_transaction=plan.transaction_id,
        )
    write_model_states(plan.root, states)
    if fail_at == "after:manifest_replaced":
        raise InjectedTransactionFailure(fail_at)
    _transition(plan, "committed", fail_at)
    shutil.rmtree(paths.migration_dir / "displaced", ignore_errors=True)
    shutil.rmtree(paths.migration_dir / "replacement", ignore_errors=True)
    return _journal_from_plan(plan, "committed")


def _depends_transitively(model_name: str, dependency: str) -> bool:
    direct = MODEL_DEPENDENCIES[model_name]
    return dependency in direct or any(
        _depends_transitively(item, dependency) for item in direct
    )


def dependent_models(
    model_name: str,
    states: dict[str, ModelAuthorityState] | None = None,
) -> tuple[str, ...]:
    target = "editorial" if model_name == "results_hierarchy" else model_name
    order = ("publication", "issue", "manuscript", "editorial", "results_hierarchy", "research")
    values = [
        name
        for name in order
        if name != model_name
        and _depends_transitively(name, target)
        and (states is None or states[name].mode == "v2-authoritative")
    ]
    return tuple(values)


def _committed_adoption(root: Path, transaction_id: str) -> TransactionJournal:
    try:
        journal = _read_journal(transaction_paths(root, transaction_id).journal_path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise TransactionError(
            MigrationFinding("transaction.journal_missing", f"/{transaction_id}", f"adoption journal cannot be read: {error}")
        ) from error
    if journal.action != "adopt" or journal.state != "committed":
        raise TransactionError(
            MigrationFinding("transaction.journal_state", f"/{transaction_id}", "rollback source must be a committed adoption")
        )
    return journal


def plan_rollback(
    root: Path,
    model_name: str,
    *,
    transaction_id: str = "",
    cascade: bool = False,
) -> RollbackPlan:
    project = root.absolute()
    states = read_model_states(project)
    requested = _affected(model_name)
    if all(states[name].mode != "v2-authoritative" for name in requested):
        existed, digest = _manifest_identity(project)
        return RollbackPlan(project, model_name, "", requested, (), {}, {}, existed, digest, digest, True)
    blockers = tuple(name for name in dependent_models(model_name, states) if name not in requested)
    if blockers and not cascade:
        raise TransactionError(
            MigrationFinding("transaction.dependent", f"/models/{model_name}", "v2 dependent models block rollback: " + ", ".join(blockers))
        )
    selected: set[str] = set(requested)
    if cascade:
        for name in blockers:
            selected.update(_affected(name))
    order = ("publication", "issue", "manuscript", "editorial", "results_hierarchy", "research")
    models = tuple(name for name in order if name in selected and states[name].mode == "v2-authoritative")
    targets: dict[str, TransactionTarget] = {}
    restore_transactions: dict[str, str] = {}
    result_states: dict[str, ModelAuthorityState] = {}
    verified_snapshots: set[str] = set()
    for name in models:
        source_transaction = transaction_id if name in requested and transaction_id else states[name].last_adopt_transaction
        if not source_transaction:
            raise TransactionError(
                MigrationFinding("transaction.snapshot_missing", f"/models/{name}", "model has no adoption transaction to roll back")
            )
        if transaction_id and name in requested and states[name].last_adopt_transaction != transaction_id:
            raise TransactionError(
                MigrationFinding("transaction.target_changed", f"/models/{name}", "specific transaction is not the model's current adoption")
            )
        journal = _committed_adoption(project, source_transaction)
        if source_transaction not in verified_snapshots:
            snapshot_findings = verify_snapshot(project, source_transaction)
            if snapshot_findings:
                raise TransactionError(snapshot_findings[0])
            verified_snapshots.add(source_transaction)
        snapshot_root = project / ".paperops/snapshots" / source_transaction
        snapshot_states = read_model_states(snapshot_root)
        result_states[name] = snapshot_states[name]
        relative = _TARGETS[name]
        if relative in targets:
            continue
        journal_target = next((item for item in journal.targets if item.relative_path == relative), None)
        if journal_target is None:
            raise TransactionError(
                MigrationFinding("transaction.snapshot_manifest", f"/{relative}", "adoption journal does not cover the model target")
            )
        current = project / relative
        if not current.exists() or _path_hash(current) != journal_target.candidate_hash:
            raise TransactionError(
                MigrationFinding("transaction.target_changed", f"/{relative}", "current model differs from the committed adoption")
            )
        source = snapshot_root / relative
        if journal_target.old_exists and not source.exists():
            raise TransactionError(
                MigrationFinding("transaction.snapshot_missing", f"/{relative}", "rollback target is missing from the snapshot")
            )
        targets[relative] = TransactionTarget(
            relative,
            True,
            _path_hash(current),
            _path_hash(source) if journal_target.old_exists else "",
        )
        restore_transactions[relative] = source_transaction
    rollback_id = new_transaction_id(datetime.now(UTC), secrets.token_bytes(24))
    manifest_existed, manifest_hash = _manifest_identity(project)
    future_states = dict(states)
    future_states.update(result_states)
    manifest_candidate_hash = _future_manifest_hash(project, future_states)
    return RollbackPlan(
        project,
        model_name,
        rollback_id,
        models,
        tuple(targets.values()),
        restore_transactions,
        result_states,
        manifest_existed,
        manifest_hash,
        manifest_candidate_hash,
    )


def _rollback_journal(plan: RollbackPlan, state: str) -> TransactionJournal:
    return TransactionJournal(
        1,
        plan.transaction_id,
        "rollback",
        plan.model_name,
        plan.models,
        state,
        plan.targets,
        {name: value.current_hash for name, value in plan.result_states.items()},
        plan.manifest_existed,
        plan.manifest_hash,
        plan.manifest_candidate_hash,
    )


def _rollback_transition(plan: RollbackPlan, state: str, fail_at: str) -> None:
    if fail_at == f"before:{state}":
        raise InjectedTransactionFailure(fail_at)
    _write_journal(plan.root, _rollback_journal(plan, state))
    if fail_at == f"after:{state}":
        raise InjectedTransactionFailure(fail_at)


def execute_rollback(plan: RollbackPlan, *, fail_at: str = "") -> TransactionJournal:
    if plan.no_op:
        return _rollback_journal(plan, "committed")
    _rollback_transition(plan, "planned", fail_at)
    paths = transaction_paths(plan.root, plan.transaction_id)
    for target in plan.targets:
        source_transaction = plan.restore_transactions[target.relative_path]
        source = plan.root / ".paperops/snapshots" / source_transaction / target.relative_path
        destination = paths.candidate_dir / target.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if target.candidate_hash:
            if source.is_dir():
                shutil.copytree(source, destination, copy_function=shutil.copy2)
            else:
                shutil.copy2(source, destination)
    _rollback_transition(plan, "materialized", fail_at)
    for target in plan.targets:
        current = plan.root / target.relative_path
        if not current.exists() or _path_hash(current) != target.old_hash:
            raise TransactionError(
                MigrationFinding("transaction.target_changed", f"/{target.relative_path}", "current target changed after rollback planning")
            )
    _rollback_transition(plan, "validated", fail_at)
    snapshot_inputs = [Path(item.relative_path) for item in plan.targets]
    if plan.manifest_existed:
        snapshot_inputs.append(Path(".pops/manifest.toml"))
    snapshot_paths(plan.root, plan.transaction_id, tuple(snapshot_inputs))
    _rollback_transition(plan, "snapshotted", fail_at)
    _rollback_transition(plan, "replacing", fail_at)
    for target in plan.targets:
        current = plan.root / target.relative_path
        replacement = paths.candidate_dir / target.relative_path
        displaced = paths.migration_dir / "displaced" / target.relative_path
        displaced.parent.mkdir(parents=True, exist_ok=True)
        os.replace(current, displaced)
        if target.candidate_hash:
            current.parent.mkdir(parents=True, exist_ok=True)
            os.replace(replacement, current)
    if fail_at == "after:targets_replaced":
        raise InjectedTransactionFailure(fail_at)
    states = read_model_states(plan.root)
    states.update(plan.result_states)
    write_model_states(plan.root, states)
    if fail_at == "after:manifest_replaced":
        raise InjectedTransactionFailure(fail_at)
    _rollback_transition(plan, "committed", fail_at)
    shutil.rmtree(paths.migration_dir / "displaced", ignore_errors=True)
    return _rollback_journal(plan, "committed")


def _read_journal(path: Path) -> TransactionJournal:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("state") not in JOURNAL_STATES:
        raise ValueError("unsupported journal")
    return TransactionJournal(
        1,
        str(payload["transaction_id"]),
        str(payload["action"]),
        str(payload["model_name"]),
        tuple(payload["models"]),
        str(payload["state"]),
        tuple(TransactionTarget(**item) for item in payload["targets"]),
        dict(payload["state_hashes"]),
        bool(payload["manifest_existed"]),
        str(payload["manifest_hash"]),
        str(payload["manifest_candidate_hash"]),
    )


def _restore_path(root: Path, snapshot_root: Path, relative: str, existed: bool) -> None:
    target = root / relative
    _remove(target)
    if not existed:
        return
    source = snapshot_root / relative
    temporary = target.with_name(f".{target.name}.restore-{os.getpid()}")
    _remove(temporary)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
    else:
        shutil.copy2(source, temporary)
    os.replace(temporary, target)


def _mark(root: Path, journal: TransactionJournal, state: str) -> None:
    _write_journal(
        root,
        TransactionJournal(
            journal.schema_version,
            journal.transaction_id,
            journal.action,
            journal.model_name,
            journal.models,
            state,
            journal.targets,
            journal.state_hashes,
            journal.manifest_existed,
            journal.manifest_hash,
            journal.manifest_candidate_hash,
        ),
    )


def recover_incomplete_transactions(root: Path) -> tuple[MigrationFinding, ...]:
    project = root.absolute()
    findings: list[MigrationFinding] = []
    migrations = project / ".paperops/migrations"
    if not migrations.is_dir():
        return ()
    for path in sorted(migrations.glob("*/journal.json")):
        try:
            journal = _read_journal(path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            findings.append(MigrationFinding("recovery.journal_invalid", "/journal.json", f"transaction journal is invalid: {error}"))
            continue
        if journal.state in {"committed", "rolled_back", "conflict"}:
            continue
        known = True
        changed = False
        for target in journal.targets:
            current = project / target.relative_path
            if not current.exists():
                actual = ""
            else:
                try:
                    actual = _path_hash(current)
                except TransactionError:
                    known = False
                    break
            if actual == target.old_hash and actual != "":
                continue
            if not target.old_exists and actual == "":
                continue
            if actual == target.candidate_hash or actual == "":
                changed = True
                continue
            known = False
            break
        manifest_exists, manifest_hash = _manifest_identity(project)
        manifest_known = (
            (manifest_exists == journal.manifest_existed and manifest_hash == journal.manifest_hash)
            or (manifest_exists and manifest_hash == journal.manifest_candidate_hash)
        )
        if not known or not manifest_known:
            _mark(project, journal, "conflict")
            findings.append(MigrationFinding("recovery.conflict", f"/{journal.transaction_id}", "tracked state contains an unknown manual edit; recovery did not overwrite it"))
            continue
        if changed:
            snapshot_findings = verify_snapshot(project, journal.transaction_id)
            if snapshot_findings:
                _mark(project, journal, "conflict")
                findings.extend(snapshot_findings)
                findings.append(MigrationFinding("recovery.conflict", f"/{journal.transaction_id}", "snapshot verification failed"))
                continue
            snapshot_root = project / ".paperops/snapshots" / journal.transaction_id
            for target in journal.targets:
                _restore_path(project, snapshot_root, target.relative_path, target.old_exists)
            _restore_path(project, snapshot_root, ".pops/manifest.toml", journal.manifest_existed)
        _mark(project, journal, "rolled_back")
    return tuple(findings)
