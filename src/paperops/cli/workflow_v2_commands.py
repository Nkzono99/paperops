"""Thin CLI adapters for the typed workflow kernel."""

from __future__ import annotations

import json
import os
from pathlib import Path

from paperops.workflow_v2.catalog import load_workflow_catalog
from paperops.workflow_v2.graph import build_dependency_graph, plan_workflow_impact
from paperops.workflow_v2.profile import load_workflow_profile
from paperops.workflow_v2.projection import project_workflow_status
from paperops.workflow_v2.approvals import inspect_approvals, plan_approval_decision
from paperops.workflow_v2.issues import inspect_issues, plan_issue_close, plan_issue_reopen, plan_issue_route
from paperops.workflow_v2.transaction import execute_workflow_apply, execute_workflow_rollback


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def workflow_v2_status(root: Path, *, json_output: bool) -> int:
    profile = load_workflow_profile(root)
    snapshot = load_workflow_catalog(root)
    result = project_workflow_status(snapshot, build_dependency_graph(snapshot), profile)
    payload = result.to_dict()
    if json_output:
        print(_canonical(payload), end="")
    else:
        print(f"workflow stage: {result.stage}")
        print(f"review: {result.review_axis}")
        print(f"submission: {result.submission_axis}")
        print(f"stale impacts: {len(result.stale_impacts)}")
    return 1 if any(row.severity == "error" for row in result.reasons) else 0


def workflow_v2_plan(root: Path, *, changed: tuple[str, ...], issues: tuple[str, ...], json_output: bool) -> int:
    load_workflow_profile(root)
    graph = build_dependency_graph(load_workflow_catalog(root))
    result = plan_workflow_impact(graph, changed_ids=changed, issue_ids=issues)
    payload = result.to_dict()
    directory = root / ".paperops/workflow/plans" / result.plan_id
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".plan.{os.getpid()}.tmp"
    temporary.write_text(_canonical(payload), encoding="utf-8")
    os.replace(temporary, directory / "plan.json")
    if json_output:
        print(_canonical(payload), end="")
    else:
        print(f"workflow plan: {result.plan_id}")
        print(f"ready: {'yes' if result.ready else 'no'}")
        for impact in result.impacts:
            if impact.impact != "unaffected":
                print(f"- {impact.target_id}: {impact.impact} ({impact.relation})")
    return 0 if result.ready else 1


def workflow_v2_mutation(args, root: Path) -> int:
    action = args.workflow_action
    if action == "issue":
        subaction = args.issue_action
        if subaction == "status":
            payload = {"issues": list(inspect_issues(root, args.issue_id).issues)}
        elif subaction == "route":
            payload = plan_issue_route(root, args.issue_id, args.route, args.reason).to_dict()
        elif subaction == "close":
            payload = plan_issue_close(root, args.issue_id, args.reason, tuple(args.verification)).to_dict()
        elif subaction == "reopen":
            payload = plan_issue_reopen(root, args.issue_id, args.reason).to_dict()
        else:
            raise ValueError("unknown issue action")
    elif action == "approval":
        if args.approval_action == "status":
            result = inspect_approvals(root, args.target_id)
            payload = {"target_id": result.target_id, "approvals": list(result.approvals)}
        elif args.approval_action == "decide":
            payload = plan_approval_decision(root, args.target_id, args.kind, args.decision, args.reason, args.profile).to_dict()
        else:
            raise ValueError("unknown approval action")
    elif action == "apply":
        if not args.yes:
            print("error: workflow apply requires --yes.", file=__import__("sys").stderr)
            return 2
        payload = {"transaction_id": execute_workflow_apply(root, args.plan_id, confirmed=True), "state": "APPLIED"}
    elif action == "rollback":
        if not args.yes:
            print("error: workflow rollback requires --yes.", file=__import__("sys").stderr)
            return 2
        payload = {"transaction_id": execute_workflow_rollback(root, args.transaction_id, confirmed=True), "state": "ROLLED_BACK"}
    else:
        raise ValueError("unknown typed workflow action")
    if getattr(args, "json", False):
        print(_canonical(payload), end="")
    elif "plan_id" in payload:
        print(f"workflow plan: {payload['plan_id']}")
    elif "transaction_id" in payload:
        print(f"workflow transaction: {payload['transaction_id']} ({payload['state']})")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0
