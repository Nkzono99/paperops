"""Shared immutable mutation-plan representation and typed document lookup."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from paperops.compiler.privacy import scan_private_material
from paperops.compiler.safe_fs import SafeProjectReader


@dataclass(frozen=True)
class DocumentRef:
    identity: str
    content_hash: str
    document: dict[str, Any]


@dataclass(frozen=True)
class WorkflowMutationPlan:
    plan_id: str
    operation: str
    replacements: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "plan_id": self.plan_id, "operation": self.operation, "replacements": [copy.deepcopy(row) for row in self.replacements]}


def canonical_json(value: object, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def raw_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def semantic_hash(document: dict[str, Any]) -> str:
    value = copy.deepcopy(document)
    value.pop("approvals", None)
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("updated_at", None)
    return raw_hash(canonical_json(value).rstrip("\n").encode("utf-8"))


def load_documents(root: Path) -> dict[str, DocumentRef]:
    result: dict[str, DocumentRef] = {}
    with SafeProjectReader(root) as reader:
        rows = reader.read_tree_files("_paperops/model", suffixes=(".yml", ".yaml"))
    for content, metadata in rows:
        try:
            document = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeError, yaml.YAMLError):
            continue
        if not isinstance(document, dict):
            continue
        object_id = document.get("id") or document.get("model_id")
        if isinstance(object_id, str) and object_id:
            if object_id in result:
                raise ValueError("typed object id is duplicated")
            result[object_id] = DocumentRef(metadata.identity, metadata.content_hash, document)
    return result


def replacement(ref: DocumentRef, document: dict[str, Any]) -> dict[str, Any]:
    return {"identity": ref.identity, "before_hash": ref.content_hash, "content": canonical_json(document, pretty=True)}


def new_replacement(identity: str, document: dict[str, Any]) -> dict[str, Any]:
    validate_identity(identity)
    return {"identity": identity, "before_hash": "", "content": canonical_json(document, pretty=True)}


def with_index_replacement(root: Path, ref: DocumentRef, document: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    if document.get("record_type") != "workflow_issue":
        return
    index_identity = "_paperops/model/issues/index.yml"
    with SafeProjectReader(root) as reader:
        optional = reader.read_optional_file(index_identity)
    if optional is None:
        return
    content, metadata = optional
    index = yaml.safe_load(content.decode("utf-8"))
    if not isinstance(index, dict) or not isinstance(index.get("records"), list):
        raise ValueError("Issue index is invalid")
    changed = False
    for row in index["records"]:
        if isinstance(row, dict) and row.get("id") == document.get("id"):
            row["expected_revision"] = document["revision"]
            row["expected_hash"] = semantic_hash(document)
            changed = True
    if changed:
        index["index_revision"] = int(index.get("index_revision", 0)) + 1
        index_ref = DocumentRef(index_identity, metadata.content_hash, index)
        rows.append(replacement(index_ref, index))


def persist_plan(root: Path, operation: str, replacements: list[dict[str, Any]]) -> WorkflowMutationPlan:
    if not replacements:
        raise ValueError("mutation plan has no changes")
    payload = {"operation": operation, "replacements": sorted(replacements, key=lambda row: row["identity"])}
    if scan_private_material(payload):
        raise ValueError("mutation plan contains private material")
    digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    plan = WorkflowMutationPlan(f"WPLAN-{digest[:16]}", operation, tuple(payload["replacements"]))
    directory = root / ".paperops/workflow/plans" / plan.plan_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "plan.json").write_text(canonical_json(plan.to_dict(), pretty=True), encoding="utf-8")
    return plan


def safe_reason(reason: str) -> str:
    if not isinstance(reason, str) or not reason.strip() or scan_private_material(reason):
        raise ValueError("reason must be non-private public text")
    return reason.strip()


def validate_identity(identity: str) -> None:
    path = PurePosixPath(identity)
    allowed = identity.startswith("_paperops/model/") or identity == ".pops/manifest.toml"
    if path.is_absolute() or not allowed or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe mutation identity")
