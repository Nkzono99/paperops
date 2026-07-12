"""Public CLI adapter for deterministic P3 compile operations."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from paperops.cli.project import find_project_root
from paperops.compiler.bundles import (
    BundleVerificationError,
    inspect_compile,
    prepare_bundle,
)
from paperops.compiler.compare import compare_bundles
from paperops.compiler.inputs import CompileInputError
from paperops.compiler.requests import CompileRequestError, resolve_compile_request
from paperops.compiler.types import CompileFinding
from paperops.model_migration.transaction import recover_incomplete_transactions


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class CompileCommandResult:
    action: str
    target: str
    ok: bool
    exit_code: int
    findings: tuple[CompileFinding, ...] = ()
    result: Mapping[str, Any] | None = None
    results: tuple[Mapping[str, Any], ...] = ()
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "action": self.action,
            "target": self.target,
            "ok": self.ok,
            "findings": [item.to_dict() for item in self.findings],
        }
        if self.result is not None:
            payload["result"] = dict(self.result)
        if self.action == "status":
            payload["results"] = [dict(item) for item in self.results]
        return payload


def add_compile_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    parser = subcommands.add_parser(
        "compile",
        help="Prepare and inspect typed compile bundles.",
    )
    actions = parser.add_subparsers(dest="compile_action", required=True)

    status = actions.add_parser("status", help="Inspect verified compile cache entries.")
    status.add_argument("target", nargs="?", default="all")
    _path_json(status)
    status.set_defaults(func=cmd_compile_status)

    prepare = actions.add_parser("prepare", help="Prepare a deterministic compile bundle.")
    prepare.add_argument("target")
    prepare.add_argument("path", nargs="?", type=Path)
    prepare.add_argument("--scope", choices=("block", "section", "manuscript"))
    prepare.add_argument("--block", action="append", default=[], dest="blocks")
    prepare.add_argument("--shadow", default="", dest="shadow_transaction_id")
    prepare.add_argument("--refresh", action="store_true")
    prepare.add_argument("--json", action="store_true", dest="json_output")
    prepare.set_defaults(func=cmd_compile_prepare)

    compare = actions.add_parser("compare", help="Compare two verified compile bundles.")
    compare.add_argument("left_compile_id")
    compare.add_argument("right_compile_id")
    _path_json(compare)
    compare.set_defaults(func=cmd_compile_compare)
    return parser


def _path_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")


def _root(args: argparse.Namespace) -> Path | None:
    return find_project_root((args.path or Path.cwd()).expanduser())


def _finding(code: str, pointer: str, message: str) -> CompileFinding:
    return CompileFinding(code, pointer, message)


def _error(
    action: str,
    target: str,
    code: str,
    message: str,
    exit_code: int,
) -> CompileCommandResult:
    return CompileCommandResult(
        action,
        target,
        False,
        exit_code,
        (_finding(code, "/", message),),
    )


def _preflight(
    args: argparse.Namespace,
    action: str,
    target: str,
) -> tuple[Path | None, CompileCommandResult | None]:
    root = _root(args)
    if root is None:
        return None, _error(
            action,
            target,
            "compile.project_missing",
            "no PaperOps project was found",
            2,
        )
    try:
        recovery = recover_incomplete_transactions(root)
    except Exception:
        return root, _error(
            action,
            target,
            "compile.recovery_failed",
            "incomplete model transaction recovery failed",
            1,
        )
    if recovery:
        return root, _error(
            action,
            target,
            "compile.recovery_blocked",
            "an incomplete model transaction must be resolved first",
            1,
        )
    return root, None


def _emit(args: argparse.Namespace, result: CompileCommandResult) -> int:
    payload = result.to_dict()
    if bool(getattr(args, "json_output", False)):
        print(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    else:
        print(render_compile_result(payload))
    return result.exit_code


def render_compile_result(payload: Mapping[str, object]) -> str:
    """Render a domain payload without reading external state."""
    lines = [f"compile {payload['action']}: {'ok' if payload['ok'] else 'blocked'}"]
    result = payload.get("result")
    if isinstance(result, Mapping):
        compile_id = result.get("compile_id")
        if isinstance(compile_id, str) and compile_id:
            lines.append(f"compile ID: {compile_id}")
        changes = result.get("changes", ())
        for change in changes if isinstance(changes, list) else ():
            if isinstance(change, Mapping):
                lines.append(f"changed: {change.get('field', '')}")
    results = payload.get("results")
    if isinstance(results, list):
        lines.extend(
            f"- {item.get('compile_id', '')}: {item.get('status', '')}"
            for item in results
            if isinstance(item, Mapping)
        )
    findings = payload.get("findings")
    if isinstance(findings, list):
        lines.extend(
            f"[{item.get('code', 'compile.error')}] {item.get('message', '')}"
            for item in findings
            if isinstance(item, Mapping)
        )
    return "\n".join(lines)


def cmd_compile_prepare(args: argparse.Namespace) -> int:
    root, blocked = _preflight(args, "prepare", args.target)
    if blocked is not None:
        return _emit(args, blocked)
    assert root is not None
    try:
        request = resolve_compile_request(
            root,
            args.target,
            scope=args.scope,
            block_ids=tuple(args.blocks),
            shadow_transaction_id=args.shadow_transaction_id,
        )
    except (CompileRequestError, TypeError, ValueError):
        return _emit(
            args,
            _error(
                "prepare",
                args.target,
                "compile.request_invalid",
                "compile target or scope is invalid",
                2,
            ),
        )
    except CompileInputError as error:
        return _emit(
            args,
            CompileCommandResult("prepare", args.target, False, 1, (error.finding,)),
        )
    except Exception:
        return _emit(
            args,
            _error(
                "prepare",
                args.target,
                "compile.internal_error",
                "compile operation failed",
                1,
            ),
        )
    try:
        prepared = prepare_bundle(root, request, refresh=args.refresh)
    except BundleVerificationError:
        return _emit(
            args,
            _error(
                "prepare",
                args.target,
                "compile.cache_invalid",
                "compile cache verification failed",
                1,
            ),
        )
    except Exception:
        return _emit(
            args,
            _error(
                "prepare",
                args.target,
                "compile.internal_error",
                "compile operation failed",
                1,
            ),
        )
    result = CompileCommandResult(
        "prepare",
        args.target,
        prepared.ok,
        0 if prepared.ok else 1,
        prepared.findings,
        prepared.to_dict(),
    )
    return _emit(args, result)


def cmd_compile_status(args: argparse.Namespace) -> int:
    root, blocked = _preflight(args, "status", args.target)
    if blocked is not None:
        return _emit(args, blocked)
    assert root is not None
    try:
        resolve_compile_request(root, args.target)
    except (CompileRequestError, TypeError, ValueError):
        return _emit(
            args,
            _error(
                "status",
                args.target,
                "compile.target_invalid",
                "compile target is invalid",
                2,
            ),
        )
    except CompileInputError as error:
        return _emit(
            args,
            CompileCommandResult("status", args.target, False, 1, (error.finding,)),
        )
    except Exception:
        return _emit(
            args,
            _error("status", args.target, "compile.internal_error", "compile operation failed", 1),
        )
    try:
        status = inspect_compile(root, args.target)
    except Exception:
        return _emit(
            args,
            _error("status", args.target, "compile.internal_error", "compile operation failed", 1),
        )
    return _emit(
        args,
        CompileCommandResult(
            "status",
            args.target,
            status.ok,
            0 if status.ok else 1,
            status.findings,
            results=tuple(item.to_dict() for item in status.results),
        ),
    )


def cmd_compile_compare(args: argparse.Namespace) -> int:
    target = f"{args.left_compile_id}..{args.right_compile_id}"
    root, blocked = _preflight(args, "compare", target)
    if blocked is not None:
        return _emit(args, blocked)
    assert root is not None
    if any(
        _SAFE_ID.fullmatch(value) is None
        for value in (args.left_compile_id, args.right_compile_id)
    ):
        return _emit(
            args,
            _error("compare", target, "compile.id_invalid", "compile ID is invalid", 2),
        )
    try:
        comparison = compare_bundles(root, args.left_compile_id, args.right_compile_id)
    except BundleVerificationError:
        return _emit(
            args,
            _error("compare", target, "compile.cache_invalid", "compile cache verification failed", 1),
        )
    except Exception:
        return _emit(
            args,
            _error("compare", target, "compile.internal_error", "compile operation failed", 1),
        )
    return _emit(
        args,
        CompileCommandResult("compare", target, True, 0, result=comparison.to_dict()),
    )


__all__ = [
    "CompileCommandResult",
    "add_compile_parser",
    "render_compile_result",
]
