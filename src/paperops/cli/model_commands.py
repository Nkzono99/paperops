"""High-level deterministic model operations for project users."""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paperops.cli.project import find_project_root
from paperops.model_migration.adapters import adapter_for
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.staging import (
    new_transaction_id,
    transaction_paths,
    write_report,
)
from paperops.model_migration.transaction import (
    MODEL_DEPENDENCIES,
    TransactionError,
    execute_adoption,
    execute_rollback,
    plan_adoption,
    plan_rollback,
    recover_incomplete_transactions,
)
from paperops.model_migration.types import (
    MigrationCandidate,
    MigrationFinding,
    MigrationInput,
    MigrationReport,
)
from paperops.model_state import (
    MODEL_NAMES,
    ModelAuthorityState,
    ModelStateError,
    read_model_states,
    write_model_states,
)
from paperops.model_validation import run_model_validation


@dataclass(frozen=True)
class ModelCommandResult:
    action: str
    model: str
    ok: bool
    exit_code: int
    findings: tuple[MigrationFinding, ...] = ()
    models: dict[str, dict[str, str]] | None = None
    transaction_id: str = ""
    reused: bool = False


def add_model_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    parser = subcommands.add_parser("model", help="Inspect and migrate typed model authority.")
    actions = parser.add_subparsers(dest="model_action", required=True)

    status = actions.add_parser("status", help="Show model authority state.")
    status.add_argument("model", choices=("all", *MODEL_NAMES), nargs="?", default="all")
    _common(status)
    status.set_defaults(func=cmd_model_status)

    validate = actions.add_parser("validate", help="Run the managed model checker.")
    validate.add_argument("model", choices=("all", *MODEL_NAMES))
    validate.add_argument("path", nargs="?", type=Path)
    validate.add_argument("--json", action="store_true", dest="json_output")
    validate.add_argument("--strict", action="store_true")
    validate.set_defaults(func=cmd_model_validate)

    diff = actions.add_parser("diff", help="Generate and validate a shadow candidate.")
    diff.add_argument("model", choices=MODEL_NAMES)
    diff.add_argument("path", nargs="?", type=Path)
    diff.add_argument("--json", action="store_true", dest="json_output")
    diff.add_argument("--refresh", action="store_true")
    diff.set_defaults(func=cmd_model_diff)

    adopt = actions.add_parser("adopt", help="Adopt a validated shadow candidate.")
    adopt.add_argument("model", choices=MODEL_NAMES)
    adopt.add_argument("path", nargs="?", type=Path)
    adopt.add_argument("--json", action="store_true", dest="json_output")
    adopt.add_argument("--yes", action="store_true")
    adopt.add_argument("--dry-run", action="store_true")
    adopt.set_defaults(func=cmd_model_adopt)

    rollback = actions.add_parser("rollback", help="Restore a model snapshot.")
    rollback.add_argument("model", choices=MODEL_NAMES)
    rollback.add_argument("path", nargs="?", type=Path)
    rollback.add_argument("--json", action="store_true", dest="json_output")
    rollback.add_argument("--cascade", action="store_true")
    rollback.add_argument("--dry-run", action="store_true")
    rollback.add_argument("--transaction", default="")
    rollback.set_defaults(func=cmd_model_rollback)
    return parser


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")


def _root(args: argparse.Namespace) -> Path | None:
    start = (args.path or Path.cwd()).expanduser()
    return find_project_root(start)


def _project_missing(action: str, model: str) -> ModelCommandResult:
    return ModelCommandResult(
        action,
        model,
        False,
        2,
        (MigrationFinding("state.project_missing", "/", "no PaperOps project was found"),),
    )


def _public_message(message: str, root: Path) -> str:
    rendered = message.replace(str(root) + "/", "").replace(str(root), ".")
    return rendered


def _emit(args: argparse.Namespace, result: ModelCommandResult) -> int:
    print(render_model_result(result, bool(getattr(args, "json_output", False))))
    return result.exit_code


def _recovery_block(root: Path, action: str, model: str) -> ModelCommandResult | None:
    findings = recover_incomplete_transactions(root)
    if not findings:
        return None
    return ModelCommandResult(action, model, False, 1, findings)


def cmd_model_status(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        return _emit(args, _project_missing("status", args.model))
    recovery = _recovery_block(root, "status", args.model)
    if recovery is not None:
        return _emit(args, recovery)
    try:
        states = read_model_states(root)
    except ModelStateError as error:
        return _emit(args, ModelCommandResult("status", args.model, False, 1, (MigrationFinding("state.invalid", "/models", str(error)),)))
    selected = MODEL_NAMES if args.model == "all" else (args.model,)
    findings: list[MigrationFinding] = []
    if any(state.origin == "init-v2" for state in states.values()):
        validation = run_model_validation(root, "all", phase="all", strict=False)
        if not validation.ok:
            findings.extend(
                MigrationFinding(
                    finding.code,
                    finding.pointer,
                    finding.message,
                    finding.severity,
                )
                for finding in validation.findings
                if finding.severity == "error"
            )
        else:
            for name in MODEL_NAMES:
                if validation.hashes.get(name, "") != states[name].current_hash:
                    findings.append(
                        MigrationFinding(
                            "state.hash_mismatch",
                            f"/models/{name}/current_hash",
                            "live model hash differs from init-v2 authority state",
                        )
                    )
    models: dict[str, dict[str, str]] = {}
    for name in selected:
        state = states[name]
        models[name] = asdict(state)
        models[name]["blocking_dependencies"] = ",".join(
            dependency
            for dependency in MODEL_DEPENDENCIES[name]
            if states[dependency].mode != "v2-authoritative"
        )
        if state.mode == "shadow-compare":
            report = root / ".paperops/migrations" / state.last_shadow_transaction / "report.json"
            candidate = root / ".paperops/migrations" / state.last_shadow_transaction / "candidate"
            if not state.last_shadow_transaction or not report.is_file() or not candidate.is_dir():
                findings.append(MigrationFinding("state.inconsistent", f"/models/{name}", "shadow state has no readable transaction report"))
        elif state.mode == "v2-authoritative":
            try:
                plan_adoption(root, name)
            except TransactionError as error:
                findings.append(error.finding)
    return _emit(args, ModelCommandResult("status", args.model, not findings, 0 if not findings else 1, tuple(findings), models))


def cmd_model_validate(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        return _emit(args, _project_missing("validate", args.model))
    recovery = _recovery_block(root, "validate", args.model)
    if recovery is not None:
        return _emit(args, recovery)
    selected = MODEL_NAMES if args.model == "all" else (args.model,)
    findings: list[MigrationFinding] = []
    for name in selected:
        validation = run_model_validation(root, name, strict=args.strict)
        findings.extend(MigrationFinding(item.code, item.pointer, _public_message(item.message, root), item.severity) for item in validation.findings)
    return _emit(args, ModelCommandResult("validate", args.model, not any(item.severity == "error" for item in findings), 0 if not any(item.severity == "error" for item in findings) else 1, tuple(findings)))


def _write_candidate(base: Path, candidate: MigrationCandidate) -> None:
    for document in candidate.documents:
        relative = Path(document.relative_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in document.relative_path:
            raise ValueError(f"unsafe candidate path: {document.relative_path}")
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(document.content)


def _candidate_validation(root: Path, candidate: MigrationCandidate) -> tuple[MigrationFinding, ...]:
    with tempfile.TemporaryDirectory(prefix="pops-model-validate-") as tmp:
        target = Path(tmp) / "project"
        shutil.copytree(
            root,
            target,
            ignore=shutil.ignore_patterns(".git", ".paperops", "__pycache__", "*.pyc"),
        )
        prefixes = {Path(item.relative_path).parts[:3] for item in candidate.documents}
        for parts in prefixes:
            if len(parts) == 3 and parts[:2] == ("_paperops", "model"):
                existing = target.joinpath(*parts)
                if existing.is_dir():
                    shutil.rmtree(existing)
        _write_candidate(target, candidate)
        names = ("editorial", "results_hierarchy") if candidate.model_name == "editorial" else (candidate.model_name,)
        findings: list[MigrationFinding] = []
        for name in names:
            validation = run_model_validation(target, name, strict=True)
            findings.extend(MigrationFinding(item.code, item.pointer, _public_message(item.message, target), item.severity) for item in validation.findings)
        return tuple(findings)


def _load_existing_diff(root: Path, model: str, state: ModelAuthorityState) -> ModelCommandResult | None:
    if state.mode != "shadow-compare" or not state.last_shadow_transaction:
        return None
    report_path = root / ".paperops/migrations" / state.last_shadow_transaction / "report.json"
    try:
        payload = json.loads(report_path.read_text())
        findings = tuple(MigrationFinding(**item) for item in payload.get("findings", []))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    failed = any(item.severity == "error" for item in findings)
    return ModelCommandResult("diff", model, not failed, 1 if failed else 0, findings, transaction_id=state.last_shadow_transaction, reused=True)


def cmd_model_diff(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        return _emit(args, _project_missing("diff", args.model))
    recovery = _recovery_block(root, "diff", args.model)
    if recovery is not None:
        return _emit(args, recovery)
    try:
        states = read_model_states(root)
    except ModelStateError as error:
        return _emit(args, ModelCommandResult("diff", args.model, False, 1, (MigrationFinding("state.invalid", "/models", str(error)),)))
    if not args.refresh:
        existing = _load_existing_diff(root, args.model, states[args.model])
        if existing is not None:
            return _emit(args, existing)
    transaction_id = new_transaction_id(datetime.now(UTC), secrets.token_bytes(24))
    paths = transaction_paths(root, transaction_id)
    try:
        candidate = adapter_for(args.model).materialize(MigrationInput(root, args.model, ()))
        _write_candidate(paths.candidate_dir, candidate)
        findings = [*candidate.findings, *validate_conservation(candidate.inventory, candidate)]
        if not any(item.severity == "error" for item in findings):
            findings.extend(_candidate_validation(root, candidate))
    except Exception as error:
        candidate = MigrationCandidate(args.model, (), (), ())
        findings = [MigrationFinding("migration.execution", "/", f"candidate generation failed: {_public_message(str(error), root)}")]
    report = MigrationReport(1, transaction_id, args.model, 1, candidate.inventory, candidate.documents, tuple(findings))
    write_report(paths, report)
    failed = any(item.severity == "error" for item in findings)
    if not failed:
        updated = dict(states)
        affected = ("editorial", "results_hierarchy") if args.model in {"editorial", "results_hierarchy"} else (args.model,)
        for name in affected:
            updated[name] = replace(updated[name], mode="shadow-compare", last_shadow_transaction=transaction_id)
        write_model_states(root, updated)
    result = ModelCommandResult("diff", args.model, not failed, 1 if failed else 0, tuple(findings), transaction_id=transaction_id)
    return _emit(args, result)


def cmd_model_pending(args: argparse.Namespace) -> int:
    return _emit(args, ModelCommandResult(args.model_action, args.model, False, 2, (MigrationFinding("state.not_implemented", "/", "this action is not available until transaction support is installed"),)))


def cmd_model_adopt(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        return _emit(args, _project_missing("adopt", args.model))
    recovery = _recovery_block(root, "adopt", args.model)
    if recovery is not None:
        return _emit(args, recovery)
    if not args.dry_run and not args.yes:
        return _emit(
            args,
            ModelCommandResult(
                "adopt",
                args.model,
                False,
                2,
                (MigrationFinding("transaction.confirmation", "/", "pass --yes to adopt a validated shadow"),),
            ),
        )
    try:
        plan = plan_adoption(root, args.model)
        if not args.dry_run:
            execute_adoption(plan)
    except TransactionError as error:
        return _emit(args, ModelCommandResult("adopt", args.model, False, 1, (error.finding,)))
    except Exception as error:
        return _emit(
            args,
            ModelCommandResult(
                "adopt",
                args.model,
                False,
                1,
                (MigrationFinding("transaction.interrupted", "/", _public_message(str(error), root)),),
                transaction_id=getattr(locals().get("plan"), "transaction_id", ""),
            ),
        )
    return _emit(
        args,
        ModelCommandResult(
            "adopt",
            args.model,
            True,
            0,
            transaction_id=plan.transaction_id,
            reused=plan.no_op,
        ),
    )


def cmd_model_rollback(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        return _emit(args, _project_missing("rollback", args.model))
    recovery = _recovery_block(root, "rollback", args.model)
    if recovery is not None:
        return _emit(args, recovery)
    try:
        plan = plan_rollback(
            root,
            args.model,
            transaction_id=args.transaction,
            cascade=args.cascade,
        )
        if not args.dry_run:
            execute_rollback(plan)
    except TransactionError as error:
        return _emit(args, ModelCommandResult("rollback", args.model, False, 1, (error.finding,)))
    except Exception as error:
        return _emit(
            args,
            ModelCommandResult(
                "rollback",
                args.model,
                False,
                1,
                (MigrationFinding("transaction.interrupted", "/", _public_message(str(error), root)),),
                transaction_id=getattr(locals().get("plan"), "transaction_id", ""),
            ),
        )
    return _emit(
        args,
        ModelCommandResult(
            "rollback",
            args.model,
            True,
            0,
            transaction_id=plan.transaction_id,
            reused=plan.no_op,
        ),
    )


def render_model_result(result: ModelCommandResult, json_output: bool) -> str:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "action": result.action,
        "model": result.model,
        "ok": result.ok,
        "reused": result.reused,
        "findings": [asdict(item) for item in result.findings],
    }
    if result.models is not None:
        payload["models"] = result.models
    if result.transaction_id:
        payload["transaction_id"] = result.transaction_id
    if json_output:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lines = [f"model {result.action}: {'ok' if result.ok else 'blocked'}"]
    if result.models:
        lines.extend(f"- {name}: {value['mode']}" for name, value in result.models.items())
    if result.transaction_id:
        lines.append(f"- transaction: {result.transaction_id}{' (reused)' if result.reused else ''}")
    lines.extend(f"- [{item.severity}] {item.code} {item.pointer}: {item.message}" for item in result.findings)
    return "\n".join(lines)
