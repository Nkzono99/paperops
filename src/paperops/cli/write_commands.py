"""Public CLI adapter for the validated P3 Writer lifecycle."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from paperops.cli.project import find_project_root
from paperops.compiler.safe_fs import SafeCaptureError
from paperops.compiler.types import CompileFinding
from paperops.compiler.write_transaction import (
    WriteTransactionError,
    execute_write_apply,
    execute_write_rollback,
    plan_write_apply,
    plan_write_rollback,
    recover_incomplete_writes,
)
from paperops.compiler.writer import (
    build_patch,
    inspect_writer_session,
    start_writer_session,
)
from paperops.model_migration.transaction import recover_incomplete_transactions


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class WriteCommandResult:
    action: str
    ok: bool
    status: str
    exit_code: int
    session_id: str = ""
    transaction_id: str = ""
    reused: bool = False
    findings: tuple[CompileFinding, ...] = ()
    result: Mapping[str, Any] | None = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "action": self.action,
            "ok": self.ok,
            "status": self.status,
            "reused": self.reused,
            "session_id": self.session_id,
            "transaction_id": self.transaction_id,
            "findings": [item.to_dict() for item in self.findings],
        }
        if self.result is not None:
            payload["result"] = dict(self.result)
        return payload


def add_write_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    parser = subcommands.add_parser("write", help="Manage validated Writer TeX candidates.")
    actions = parser.add_subparsers(dest="write_action", required=True)
    for name, handler, noun in (
        ("start", cmd_write_start, "compile_id"),
        ("status", cmd_write_status, "session_id"),
        ("check", cmd_write_check, "session_id"),
        ("diff", cmd_write_diff, "session_id"),
        ("apply", cmd_write_apply, "session_id"),
        ("rollback", cmd_write_rollback, "transaction_id"),
    ):
        action = actions.add_parser(name)
        action.add_argument(noun)
        action.add_argument("path", nargs="?", type=Path)
        if name == "apply":
            action.add_argument("--yes", action="store_true")
        action.add_argument("--json", action="store_true", dest="json_output")
        action.set_defaults(func=handler)
    return parser


def _finding(code: str, message: str) -> CompileFinding:
    return CompileFinding(code, "/", message)


def _blocked(action: str, code: str, message: str, exit_code: int = 1, **ids: str) -> WriteCommandResult:
    return WriteCommandResult(
        action, False, "blocked", exit_code,
        session_id=ids.get("session_id", ""),
        transaction_id=ids.get("transaction_id", ""),
        findings=(_finding(code, message),),
    )


def _id(args: argparse.Namespace) -> str:
    return str(
        getattr(args, "compile_id", "")
        or getattr(args, "session_id", "")
        or getattr(args, "transaction_id", "")
    )


def _preflight(args: argparse.Namespace) -> tuple[Path | None, WriteCommandResult | None]:
    action = str(args.write_action)
    identifier = _id(args)
    id_fields = {
        "session_id": str(getattr(args, "session_id", "")),
        "transaction_id": str(getattr(args, "transaction_id", "")),
    }
    if _SAFE_ID.fullmatch(identifier) is None:
        return None, _blocked(action, "write.id_invalid", "write identifier is invalid", 2, **id_fields)
    root = find_project_root((args.path or Path.cwd()).expanduser())
    if root is None:
        return None, _blocked(action, "write.project_missing", "no PaperOps project was found", 2, **id_fields)
    try:
        p2 = recover_incomplete_transactions(root)
    except Exception:
        return root, _blocked(action, "write.recovery_failed", "model transaction recovery failed", **id_fields)
    try:
        p3 = recover_incomplete_writes(root)
    except Exception:
        return root, _blocked(action, "write.recovery_failed", "Writer transaction recovery failed", **id_fields)
    if p2 or p3:
        return root, WriteCommandResult(
            action, False, "conflict", 1,
            session_id=id_fields["session_id"],
            transaction_id=id_fields["transaction_id"],
            findings=tuple(
                [
                    _finding("write.model_recovery_blocked", "an incomplete model transaction must be resolved first")
                    for _item in p2
                ]
                + list(p3)
            ),
        )
    return root, None


def _emit(args: argparse.Namespace, result: WriteCommandResult) -> int:
    payload = result.to_dict()
    if bool(args.json_output):
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    else:
        print(render_write_result(payload))
    return result.exit_code


def render_write_result(payload: Mapping[str, object]) -> str:
    """Render a public domain payload without filesystem access."""
    lines = [f"write {payload['action']}: {payload['status']}"]
    for label, field in (("session ID", "session_id"), ("transaction ID", "transaction_id")):
        value = payload.get(field)
        if isinstance(value, str) and value:
            lines.append(f"{label}: {value}")
    result = payload.get("result")
    if isinstance(result, Mapping):
        workspace = result.get("workspace")
        if isinstance(workspace, str) and workspace:
            lines.append(f"workspace: {workspace}")
        changes = result.get("changes", ())
        if isinstance(changes, list):
            lines.append(f"changes: {len(changes)}")
        impacts = result.get("mirror_impacts", ())
        if isinstance(impacts, list):
            lines.extend(
                f"mirror: {row.get('typed_block_id', '')} {row.get('status', '')}"
                for row in impacts if isinstance(row, Mapping)
            )
    findings = payload.get("findings", ())
    if isinstance(findings, list):
        lines.extend(
            f"[{row.get('code', 'write.error')}] {row.get('message', '')}"
            for row in findings if isinstance(row, Mapping)
        )
    return "\n".join(lines)


def _run(args: argparse.Namespace, operation) -> int:
    root, blocked = _preflight(args)
    if blocked is not None:
        return _emit(args, blocked)
    assert root is not None
    try:
        result = operation(root)
    except WriteTransactionError as error:
        code = 2 if error.finding.code == "write.confirmation_required" else 1
        return _emit(
            args,
            WriteCommandResult(
                args.write_action, False, "blocked", code,
                session_id=str(getattr(args, "session_id", "")),
                transaction_id=str(getattr(args, "transaction_id", "")),
                findings=(error.finding,),
            ),
        )
    except (SafeCaptureError, ValueError, OSError):
        return _emit(args, _blocked(args.write_action, "write.state_invalid", "Writer state is missing or invalid"))
    except Exception:
        return _emit(args, _blocked(args.write_action, "write.internal_error", "write operation failed"))
    return _emit(args, result)


def cmd_write_start(args: argparse.Namespace) -> int:
    def operation(root: Path) -> WriteCommandResult:
        item = start_writer_session(root, args.compile_id)
        return WriteCommandResult(
            "start", item.ok, item.status, 0 if item.ok else 1,
            session_id=item.session_id, reused=item.reused,
            findings=item.findings, result=item.to_dict(),
        )
    return _run(args, operation)


def cmd_write_status(args: argparse.Namespace) -> int:
    def operation(root: Path) -> WriteCommandResult:
        item = inspect_writer_session(root, args.session_id)
        return WriteCommandResult(
            "status", item.ok, item.status, 0 if item.ok else 1,
            session_id=item.session_id, reused=item.reused,
            findings=item.findings, result=item.to_dict(),
        )
    return _run(args, operation)


def _patch_result(action: str, item) -> WriteCommandResult:
    return WriteCommandResult(
        action, item.ok, item.status, 0 if item.ok else 1,
        session_id=item.session_id,
        findings=item.findings,
        result=item.to_dict(),
    )


def cmd_write_check(args: argparse.Namespace) -> int:
    return _run(args, lambda root: _patch_result("check", build_patch(root, args.session_id)))


def cmd_write_diff(args: argparse.Namespace) -> int:
    return _run(args, lambda root: _patch_result("diff", build_patch(root, args.session_id)))


def cmd_write_apply(args: argparse.Namespace) -> int:
    def operation(root: Path) -> WriteCommandResult:
        plan = plan_write_apply(root, args.session_id, confirmed=bool(args.yes))
        receipt = execute_write_apply(plan)
        return WriteCommandResult(
            "apply", receipt.ok, receipt.state, 0 if receipt.ok else 1,
            session_id=receipt.session_id,
            transaction_id=receipt.transaction_id,
            reused=receipt.no_op,
            result=receipt.to_dict(),
        )
    return _run(args, operation)


def cmd_write_rollback(args: argparse.Namespace) -> int:
    def operation(root: Path) -> WriteCommandResult:
        plan = plan_write_rollback(root, args.transaction_id)
        receipt = execute_write_rollback(plan)
        return WriteCommandResult(
            "rollback", receipt.ok, receipt.state, 0 if receipt.ok else 1,
            session_id=receipt.session_id,
            transaction_id=receipt.transaction_id,
            reused=receipt.no_op,
            result=receipt.to_dict(),
        )
    return _run(args, operation)


__all__ = ["WriteCommandResult", "add_write_parser", "render_write_result"]
