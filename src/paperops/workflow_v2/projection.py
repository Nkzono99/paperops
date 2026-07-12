"""Pure five-stage workflow projection."""

from __future__ import annotations

from paperops.workflow_v2.catalog import WorkflowCatalogSnapshot
from paperops.workflow_v2.graph import WorkflowGraph
from paperops.workflow_v2.profile import WorkflowProfile
from paperops.workflow_v2.types import MACRO_STAGES, ImpactRow, WorkflowFinding, WorkflowProjection


def project_workflow_status(snapshot: WorkflowCatalogSnapshot, graph: WorkflowGraph, profile: WorkflowProfile) -> WorkflowProjection:
    facts = snapshot.fact_map()
    stage = "INGESTED"
    reasons: list[WorkflowFinding] = list(graph.findings)
    keys = ("ingested", "modeled", "architected", "drafted", "publishable")
    for candidate, key in zip(MACRO_STAGES, keys):
        if facts.get(key) is True:
            stage = candidate
        else:
            reasons.append(WorkflowFinding(f"workflow.stage.{key}.pending", "", f"{candidate} requirements are not yet satisfied.", "info"))
            break
    sections = tuple(sorted((key.removeprefix("section:"), str(value)) for key, value in snapshot.facts if key.startswith("section:")))
    approvals = tuple(sorted((key.removeprefix("approval:"), str(value)) for key, value in snapshot.facts if key.startswith("approval:")))
    stale = tuple(
        ImpactRow(key.removeprefix("stale:"), str(value), "direct", "effective_stale")
        for key, value in snapshot.facts
        if key.startswith("stale:")
    )
    return WorkflowProjection(
        stage,
        MACRO_STAGES[: MACRO_STAGES.index(stage) + 1],
        tuple(reasons),
        str(facts.get("review_axis", "idle")),
        str(facts.get("submission_axis", "not_started")),
        sections,
        approvals,
        stale,
    )
