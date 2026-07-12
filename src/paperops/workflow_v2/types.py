"""Immutable public values for workflow projection and mutation plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


MACRO_STAGES = ("INGESTED", "MODELED", "ARCHITECTED", "DRAFTED", "PUBLISHABLE")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_IMPACT_KINDS = frozenset({"direct", "transitive", "unaffected"})
_SEVERITIES = frozenset({"error", "warning", "info"})


def _id(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"{label} is not a safe identifier")


@dataclass(frozen=True, order=True)
class WorkflowFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"

    def __post_init__(self) -> None:
        _id(self.code, "finding code")
        if self.pointer and not self.pointer.startswith("/"):
            raise ValueError("finding pointer must be a JSON Pointer")
        if self.severity not in _SEVERITIES:
            raise ValueError("invalid finding severity")

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "pointer": self.pointer, "message": self.message, "severity": self.severity}


@dataclass(frozen=True, order=True)
class WorkflowNode:
    object_id: str
    object_type: str
    revision: int
    semantic_hash: str

    def __post_init__(self) -> None:
        _id(self.object_id, "object id")
        _id(self.object_type, "object type")
        if isinstance(self.revision, bool) or self.revision < 1:
            raise ValueError("revision must be positive")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.semantic_hash):
            raise ValueError("semantic hash is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.object_id, "type": self.object_type, "revision": self.revision, "hash": self.semantic_hash}


@dataclass(frozen=True, order=True)
class WorkflowEdge:
    source_id: str
    target_id: str
    relation: str

    def __post_init__(self) -> None:
        _id(self.source_id, "edge source")
        _id(self.target_id, "edge target")
        _id(self.relation, "edge relation")

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source_id, "target": self.target_id, "relation": self.relation}


@dataclass(frozen=True, order=True)
class ImpactRow:
    changed_id: str
    target_id: str
    impact: str
    relation: str

    def __post_init__(self) -> None:
        _id(self.changed_id, "changed id")
        _id(self.target_id, "target id")
        if self.impact not in _IMPACT_KINDS:
            raise ValueError("invalid impact kind")
        _id(self.relation, "impact relation")

    def to_dict(self) -> dict[str, str]:
        return {"changed_id": self.changed_id, "target_id": self.target_id, "impact": self.impact, "relation": self.relation}


@dataclass(frozen=True)
class WorkflowImpactPlan:
    plan_id: str
    inputs_hash: str
    impacts: tuple[ImpactRow, ...]
    findings: tuple[WorkflowFinding, ...] = ()

    def __post_init__(self) -> None:
        _id(self.plan_id, "plan id")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.inputs_hash):
            raise ValueError("inputs hash is invalid")
        object.__setattr__(self, "impacts", tuple(sorted(self.impacts)))
        object.__setattr__(self, "findings", tuple(sorted(self.findings)))

    @property
    def ready(self) -> bool:
        return not any(row.severity == "error" for row in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "inputs_hash": self.inputs_hash, "ready": self.ready, "impacts": [row.to_dict() for row in self.impacts], "findings": [row.to_dict() for row in self.findings]}


@dataclass(frozen=True)
class WorkflowProjection:
    stage: str
    satisfied_stages: tuple[str, ...]
    reasons: tuple[WorkflowFinding, ...]
    review_axis: str
    submission_axis: str
    section_axis: tuple[tuple[str, str], ...]
    approval_axis: tuple[tuple[str, str], ...]
    stale_impacts: tuple[ImpactRow, ...]

    def __post_init__(self) -> None:
        if self.stage not in MACRO_STAGES:
            raise ValueError("unknown macro stage")
        expected = MACRO_STAGES[: MACRO_STAGES.index(self.stage) + 1]
        if tuple(self.satisfied_stages) != expected:
            raise ValueError("satisfied stages must be a macro-stage prefix")
        object.__setattr__(self, "reasons", tuple(sorted(self.reasons)))
        object.__setattr__(self, "section_axis", tuple(sorted(self.section_axis)))
        object.__setattr__(self, "approval_axis", tuple(sorted(self.approval_axis)))
        object.__setattr__(self, "stale_impacts", tuple(sorted(self.stale_impacts)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "satisfied_stages": list(self.satisfied_stages),
            "reasons": [row.to_dict() for row in self.reasons],
            "axes": {
                "review": self.review_axis,
                "submission": self.submission_axis,
                "sections": dict(self.section_axis),
                "approvals": dict(self.approval_axis),
            },
            "stale_impacts": [row.to_dict() for row in self.stale_impacts],
        }
