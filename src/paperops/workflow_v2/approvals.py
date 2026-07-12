"""Owner-local approval inspection and proposal generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops.workflow_v2.mutation import load_documents, persist_plan, replacement, safe_reason, semantic_hash
from paperops.workflow_v2.profile import load_workflow_profile


@dataclass(frozen=True)
class ApprovalStatusResult:
    target_id: str
    approvals: tuple[dict[str, Any], ...]


def inspect_approvals(root: Path, target_id: str = "") -> ApprovalStatusResult:
    documents = load_documents(root)
    if not target_id or target_id not in documents:
        raise ValueError("approval target is not registered")
    approvals = documents[target_id].document.get("approvals")
    if not isinstance(approvals, list):
        raise ValueError("approval target does not own an approval history")
    return ApprovalStatusResult(target_id, tuple(dict(row) for row in approvals if isinstance(row, dict)))


def plan_approval_decision(root: Path, target_id: str, kind: str, decision: str, reason: str, profile: str = ""):
    managed = load_workflow_profile(root)
    if kind not in managed.approval_kinds:
        raise ValueError("approval kind is not registered")
    if decision not in {"approved", "rejected", "revoked"}:
        raise ValueError("approval decision is invalid")
    note = safe_reason(reason)
    documents = load_documents(root)
    ref = documents.get(target_id)
    if ref is None:
        raise ValueError("approval target is not registered")
    document = dict(ref.document)
    approvals = document.get("approvals")
    if not isinstance(approvals, list):
        raise ValueError("approval target does not own an approval history")
    subject_hash = semantic_hash(document)
    numbers = [int(str(row.get("approval_id", "APR-0")).split("-")[-1]) for row in approvals if isinstance(row, dict) and str(row.get("approval_id", "")).startswith("APR-") and str(row.get("approval_id", "")).split("-")[-1].isdigit()]
    approval = {
        "approval_id": f"APR-{max(numbers, default=0) + 1:04d}",
        "kind": kind,
        "decision": decision,
        "object_revision": document.get("revision", 1),
        "object_hash": subject_hash,
        "actor": "human",
        "note": note,
    }
    document["approvals"] = [*approvals, approval]
    return persist_plan(root, "approval.decide", [replacement(ref, document)])
