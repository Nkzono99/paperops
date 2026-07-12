"""Public CLI adapter for deterministic typed model changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from paperops.change.planning import ChangePlanningError, plan_change, read_change_plan
from paperops.change.transaction import ChangeTransactionError, apply_change, rollback_change
from paperops.cli.project import find_project_root


def add_change_parser(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> argparse.ArgumentParser:
    parser = subcommands.add_parser("change", help="Plan and apply atomic typed-model changes.")
    actions = parser.add_subparsers(dest="change_action", required=True)
    plan = actions.add_parser("plan", help="Validate and cache a change request.")
    plan.add_argument("request", type=Path); _common(plan); plan.set_defaults(func=cmd_change)
    for name in ("status", "diff"):
        command = actions.add_parser(name, help=f"Show a cached change {name}.")
        command.add_argument("change_id"); _common(command); command.set_defaults(func=cmd_change)
    apply = actions.add_parser("apply", help="Apply a validated change atomically.")
    apply.add_argument("change_id"); apply.add_argument("--yes", action="store_true"); _common(apply); apply.set_defaults(func=cmd_change)
    rollback = actions.add_parser("rollback", help="Rollback a committed change transaction.")
    rollback.add_argument("transaction_id"); rollback.add_argument("--yes", action="store_true"); _common(rollback); rollback.set_defaults(func=cmd_change)
    return parser


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", type=Path, help="PaperOps project; defaults to cwd.")
    parser.add_argument("--json", action="store_true", dest="json_output")


def _root(args: argparse.Namespace) -> Path | None:
    return find_project_root((args.path or Path.cwd()).expanduser())


def _summary(plan: Any, action: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "action": action,
        "ok": True,
        "change_id": plan.change_id,
        "affected_models": list(plan.affected_models),
        "operations": [
            {
                "action": row.action,
                "model": row.model,
                "record_type": row.record_type,
                "id": row.object_id,
                "expected_revision": row.expected_revision,
                "expected_hash": row.expected_hash,
            }
            for row in plan.operations
        ],
        "impacts": sorted({row.identity for row in plan.replacements}),
        "findings": [],
    }


def _emit(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return
    if payload.get("ok"):
        if payload.get("change_id"):
            print(f"change: {payload['change_id']} ({payload['action']})")
            for row in payload.get("operations", []):
                print(f"- {row['action']} {row['model']}/{row['record_type']}/{row['id']}")
        else:
            print(f"change transaction: {payload['transaction_id']} ({payload['state']})")
    else:
        print(f"error: {payload['findings'][0]['message']}", file=sys.stderr)


def _failure(message: str) -> dict[str, Any]:
    return {"schema_version": 1, "ok": False, "findings": [{"code": "change.invalid", "severity": "error", "message": message}]}


def cmd_change(args: argparse.Namespace) -> int:
    root = _root(args)
    if root is None:
        _emit(args, _failure("no PaperOps project was found")); return 2
    action = args.change_action
    if action in {"apply", "rollback"} and not args.yes:
        _emit(args, _failure(f"change {action} requires --yes")); return 2
    try:
        if action == "plan":
            payload = _summary(plan_change(root, args.request), action)
        elif action in {"status", "diff"}:
            payload = _summary(read_change_plan(root, args.change_id), action)
        elif action == "apply":
            payload = {"schema_version": 1, "ok": True, "action": action, "transaction_id": apply_change(root, args.change_id, confirmed=True), "state": "COMMITTED", "findings": []}
        elif action == "rollback":
            payload = {"schema_version": 1, "ok": True, "action": action, "transaction_id": rollback_change(root, args.transaction_id, confirmed=True), "state": "COMMITTED", "findings": []}
        else:
            raise ChangePlanningError("unknown change action")
    except (ChangePlanningError, ChangeTransactionError, ValueError, OSError) as exc:
        message = str(exc).replace(str(root) + "/", "").replace(str(root), ".")
        _emit(args, _failure(message)); return 1
    _emit(args, payload)
    return 0
