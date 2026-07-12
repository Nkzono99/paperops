"""Independent workflow issue inspection and mutation proposals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops.workflow_v2.mutation import load_documents, persist_plan, replacement, safe_reason, with_index_replacement
from paperops.workflow_v2.profile import load_workflow_profile


@dataclass(frozen=True)
class IssueStatusResult:
    issues: tuple[dict[str, Any], ...]


def _issues(root: Path) -> dict[str, tuple[Any, dict[str, Any]]]:
    return {key: (ref, ref.document) for key, ref in load_documents(root).items() if ref.document.get("record_type") == "workflow_issue"}


def inspect_issues(root: Path, issue_id: str = "all") -> IssueStatusResult:
    issues = _issues(root)
    if issue_id != "all":
        if issue_id not in issues:
            raise ValueError("workflow issue is not registered")
        values = [issues[issue_id][1]]
    else:
        values = [row[1] for _, row in sorted(issues.items())]
    return IssueStatusResult(tuple(dict(value) for value in values))


def _plan(root: Path, issue_id: str, operation: str, mutate):
    issues = _issues(root)
    if issue_id not in issues:
        raise ValueError("workflow issue is not registered")
    ref, source = issues[issue_id]
    document = dict(source)
    mutate(document)
    document["revision"] = int(source.get("revision", 0)) + 1
    rows = [replacement(ref, document)]
    with_index_replacement(root, ref, document, rows)
    return persist_plan(root, operation, rows)


def plan_issue_route(root: Path, issue_id: str, route: str, reason: str):
    profile = load_workflow_profile(root)
    if route not in profile.routes:
        raise ValueError("issue route is not registered")
    why = safe_reason(reason)
    def mutate(document: dict[str, Any]) -> None:
        previous = str(document.get("route", ""))
        if previous == route:
            raise ValueError("issue is already on that route")
        history = document.get("route_history", [])
        if not isinstance(history, list):
            raise ValueError("route history is invalid")
        document["route"] = route
        document["status"] = "routed"
        document["route_history"] = [*history, {"from": previous, "to": route, "reason": why, "at": "", "actor": "human"}]
    return _plan(root, issue_id, "issue.route", mutate)


def plan_issue_close(root: Path, issue_id: str, reason: str, verification_refs: tuple[str, ...]):
    why = safe_reason(reason)
    if not verification_refs or not all(isinstance(row, str) and row for row in verification_refs):
        raise ValueError("issue closure requires verification refs")
    def mutate(document: dict[str, Any]) -> None:
        impacts = document.get("impacts", [])
        if not isinstance(impacts, list) or any(not isinstance(row, dict) or row.get("state") == "open" for row in impacts):
            raise ValueError("issue still has open impacts")
        if document.get("blocking_dependency_refs"):
            raise ValueError("issue still has blocking dependencies")
        document["status"] = "closed"
        document["closure"] = {"decision": "closed", "reason": why, "verification_refs": list(verification_refs)}
    return _plan(root, issue_id, "issue.close", mutate)


def plan_issue_reopen(root: Path, issue_id: str, reason: str):
    why = safe_reason(reason)
    def mutate(document: dict[str, Any]) -> None:
        if document.get("status") != "closed":
            raise ValueError("only a closed issue can be reopened")
        document["status"] = "open"
        document["closure"] = {"decision": "pending", "reason": why, "verification_refs": []}
    return _plan(root, issue_id, "issue.reopen", mutate)
