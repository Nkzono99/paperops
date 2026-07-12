"""Deterministic typed dependency graph and selective impact planning."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from paperops.workflow_v2.catalog import WorkflowCatalogSnapshot
from paperops.workflow_v2.types import ImpactRow, WorkflowEdge, WorkflowFinding, WorkflowImpactPlan, WorkflowNode


@dataclass(frozen=True)
class WorkflowGraph:
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...]
    findings: tuple[WorkflowFinding, ...]


def build_dependency_graph(snapshot: WorkflowCatalogSnapshot) -> WorkflowGraph:
    known = {node.object_id for node in snapshot.nodes}
    findings = list(snapshot.findings)
    for edge in snapshot.edges:
        if edge.source_id not in known or edge.target_id not in known:
            findings.append(WorkflowFinding("workflow.graph.dangling", "", "The dependency graph contains a dangling edge."))
    return WorkflowGraph(tuple(sorted(snapshot.nodes)), tuple(sorted(snapshot.edges)), tuple(sorted(findings)))


def plan_workflow_impact(graph: WorkflowGraph, *, changed_ids: tuple[str, ...] = (), issue_ids: tuple[str, ...] = ()) -> WorkflowImpactPlan:
    changed = tuple(sorted(set(changed_ids) | set(issue_ids)))
    known = {node.object_id for node in graph.nodes}
    findings = list(graph.findings)
    unknown = [row for row in changed if row not in known]
    if unknown:
        findings.append(WorkflowFinding("workflow.changed.unknown", "", "One or more changed ids are not registered."))
    outgoing: dict[str, list[WorkflowEdge]] = {}
    for edge in graph.edges:
        outgoing.setdefault(edge.source_id, []).append(edge)
    impacts: dict[tuple[str, str], ImpactRow] = {}
    affected: set[str] = set()
    for source in changed:
        if source not in known:
            continue
        queue: list[tuple[str, int, str]] = [(source, 0, "self")]
        seen = {source}
        while queue:
            current, depth, relation = queue.pop(0)
            if depth:
                affected.add(current)
                impact = "direct" if depth == 1 else "transitive"
                impacts[(source, current)] = ImpactRow(source, current, impact, relation)
            for edge in sorted(outgoing.get(current, ())):
                if edge.target_id not in seen:
                    seen.add(edge.target_id)
                    queue.append((edge.target_id, depth + 1, edge.relation))
        for target in sorted(known - affected - set(changed)):
            impacts.setdefault((source, target), ImpactRow(source, target, "unaffected", "none"))
    payload = {"changed": changed, "nodes": [n.to_dict() for n in graph.nodes], "edges": [e.to_dict() for e in graph.edges]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return WorkflowImpactPlan(f"WPLAN-{digest[:16]}", f"sha256:{digest}", tuple(impacts.values()), tuple(findings))
