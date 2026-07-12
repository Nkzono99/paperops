"""Safe, read-only capture of typed workflow facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paperops.compiler.safe_fs import SafeCaptureError, SafeProjectReader
from paperops.workflow_v2.types import WorkflowEdge, WorkflowFinding, WorkflowNode


@dataclass(frozen=True)
class WorkflowCatalogSnapshot:
    nodes: tuple[WorkflowNode, ...]
    edges: tuple[WorkflowEdge, ...]
    facts: tuple[tuple[str, Any], ...]
    findings: tuple[WorkflowFinding, ...]

    def fact_map(self) -> dict[str, Any]:
        return dict(self.facts)


def _semantic_hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _virtual_documents(document: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    result: list[tuple[dict[str, Any], str]] = []
    revision = document.get("revision", 1)
    specs = (
        ("story_candidates", "story_id", "story"),
        ("argument_moves", "move_id", "move"),
        ("visual_obligations", "visual_id", "visual"),
        ("items", "item_id", "results_item"),
    )
    for field, id_key, object_type in specs:
        rows = document.get(field, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            object_id = row.get(id_key) if isinstance(row, dict) else None
            if not isinstance(object_id, str) or not object_id:
                continue
            virtual = dict(row)
            virtual.update({"id": object_id, "record_type": object_type, "revision": row.get("revision", revision)})
            content = json.dumps(virtual, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            result.append((virtual, _semantic_hash(content)))
    return result


def _refs(value: object, parent_key: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            if key == "dependencies" and isinstance(item, list):
                for row in item:
                    if isinstance(row, str):
                        result.append((row, "dependency"))
                    elif isinstance(row, dict):
                        target = row.get("id") or row.get("ref") or row.get("target_ref")
                        if isinstance(target, str):
                            result.append((target, "dependency"))
            elif key.endswith("_ref") and isinstance(item, str) and item:
                result.append((item, key.removesuffix("_ref")))
            elif key.endswith("_refs") and isinstance(item, list):
                relation = key.removesuffix("_refs")
                result.extend((row, relation) for row in item if isinstance(row, str) and row)
            else:
                result.extend(_refs(item, key))
    elif isinstance(value, list):
        for item in value:
            result.extend(_refs(item, parent_key))
    return result


def load_workflow_catalog(root: Path) -> WorkflowCatalogSnapshot:
    findings: list[WorkflowFinding] = []
    documents: list[tuple[dict[str, Any], str]] = []
    try:
        with SafeProjectReader(root) as reader:
            captured = reader.read_tree_files("_paperops/model", suffixes=(".yml", ".yaml"))
    except SafeCaptureError as exc:
        raise ValueError("typed model tree is missing or unsafe") from exc
    for content, metadata in captured:
        try:
            raw = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeError, yaml.YAMLError):
            findings.append(WorkflowFinding("workflow.catalog.invalid", "", "A typed model document is invalid."))
            continue
        if not isinstance(raw, dict):
            continue
        documents.append((raw, metadata.content_hash))
        documents.extend(_virtual_documents(raw))
    nodes: dict[str, WorkflowNode] = {}
    for raw, content_hash in documents:
        object_id = raw.get("id")
        if not isinstance(object_id, str) or not object_id:
            continue
        object_type = raw.get("record_type") or raw.get("model") or raw.get("model_name") or "aggregate"
        revision = raw.get("revision", 1)
        if not isinstance(object_type, str) or not isinstance(revision, int) or revision < 1:
            findings.append(WorkflowFinding("workflow.catalog.identity", "", "A typed object has an invalid identity."))
            continue
        try:
            node = WorkflowNode(object_id, object_type, revision, content_hash)
        except ValueError:
            findings.append(WorkflowFinding("workflow.catalog.identity", "", "A typed object has an invalid identity."))
            continue
        if object_id in nodes:
            findings.append(WorkflowFinding("workflow.catalog.duplicate", "", "A typed object id is duplicated."))
        else:
            nodes[object_id] = node
    edges: set[WorkflowEdge] = set()
    for raw, _ in documents:
        dependent = raw.get("id")
        if not isinstance(dependent, str) or dependent not in nodes:
            continue
        for referenced, relation in _refs(raw):
            if referenced in nodes and referenced != dependent:
                try:
                    edges.add(WorkflowEdge(referenced, dependent, relation.replace("-", "_")))
                except ValueError:
                    findings.append(WorkflowFinding("workflow.catalog.relation", "", "A dependency relation is invalid."))
    types = {node.object_type for node in nodes.values()}
    facts: dict[str, Any] = {
        "ingested": bool(nodes),
        "modeled": bool(types & {"claim", "result", "figure", "research", "editorial", "section", "block"}),
        "architected": bool(types & {"story_move", "results_hierarchy", "section"}),
        "drafted": bool(types & {"section", "block"}),
        "publishable": bool(types & {"publication_snapshot", "submission"}),
        "review_axis": "active" if bool(types & {"review_round", "workflow_issue"}) else "idle",
        "submission_axis": "not_started",
    }
    return WorkflowCatalogSnapshot(tuple(sorted(nodes.values())), tuple(sorted(edges)), tuple(sorted(facts.items())), tuple(sorted(findings)))
