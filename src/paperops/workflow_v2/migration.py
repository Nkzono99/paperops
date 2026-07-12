"""Opt-in legacy workflow shadow conversion and adoption planning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paperops.cli.manifest import as_table, dumps_manifest_toml, read_manifest
from paperops.compiler.privacy import scan_private_material
from paperops.compiler.safe_fs import SafeProjectReader
from paperops.workflow_v2.migration_inventory import inventory_legacy_workflow
from paperops.workflow_v2.mutation import DocumentRef, new_replacement, persist_plan, raw_hash, replacement, safe_generated_dir, semantic_hash
from paperops.workflow_v2.profile import load_workflow_profile


@dataclass(frozen=True)
class WorkflowMigrationResult:
    migration_id: str
    source_hash: str
    candidates: tuple[dict[str, Any], ...]
    dispositions: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "migration_id": self.migration_id, "source_hash": self.source_hash, "candidates": list(self.candidates), "dispositions": list(self.dispositions)}


def _candidate(index: int, concern: object, routes: tuple[str, ...]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    if not isinstance(concern, dict):
        return None, {"source": f"concern-{index}", "disposition": "deferred", "reason": "unstructured legacy concern requires human mapping"}
    required = ("summary", "target_id", "target_type", "target_revision", "target_hash", "route")
    if any(key not in concern for key in required):
        return None, {"source": f"concern-{index}", "disposition": "deferred", "reason": "legacy concern lacks typed target binding"}
    summary, target_id, target_type, revision, target_hash, route = (concern[key] for key in required)
    if not isinstance(summary, str) or scan_private_material(summary):
        return None, {"source": f"concern-{index}", "disposition": "local-only", "reason": "legacy concern contains non-public text"}
    if not isinstance(target_id, str) or not isinstance(target_type, str) or not isinstance(revision, int) or not isinstance(target_hash, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", target_hash) is None or route not in routes:
        return None, {"source": f"concern-{index}", "disposition": "unsupported", "reason": "legacy typed binding is invalid"}
    issue_id = f"ISS-{index:04d}"
    document = {
        "schema_version": 1, "record_type": "workflow_issue", "id": issue_id, "revision": 1,
        "status": "open", "dependencies": [], "approvals": [], "extensions": {},
        "metadata": {"created_at": "", "updated_at": ""}, "severity": "major", "route": route,
        "targets": [{"kind": target_type, "id": target_id, "revision": revision, "hash": target_hash}],
        "review_round_ref": "", "confidentiality": "public", "public_summary": summary,
        "closure_criteria": ["The typed impact is verified and explicitly closed."], "blocking_dependency_refs": [],
        "impacts": [{"target_id": target_id, "target_type": target_type, "expected_revision": revision, "expected_hash": target_hash, "state": "open", "verification_refs": []}],
        "route_history": [], "closure": {"decision": "pending", "reason": "", "verification_refs": []},
        "escalation": {"level": "none", "reason": ""},
    }
    return document, {"source": f"concern-{index}", "disposition": "mapped", "reason": issue_id}


def prepare_workflow_shadow(root: Path, refresh: bool = False) -> WorkflowMigrationResult:
    inventory = inventory_legacy_workflow(root)
    profile = load_workflow_profile(root)
    migration_id = "WMIG-" + inventory.source_hash.removeprefix("sha256:")[:16]
    directory = safe_generated_dir(root, f".paperops/workflow/migration/{migration_id}")
    report_path = directory / "report.json"
    if report_path.exists() and not refresh:
        payload = json.loads(report_path.read_text())
        return WorkflowMigrationResult(payload["migration_id"], payload["source_hash"], tuple(payload["candidates"]), tuple(payload["dispositions"]))
    candidates = []
    dispositions = []
    for index, concern in enumerate(inventory.concerns, start=1):
        document, disposition = _candidate(index, concern, profile.routes)
        dispositions.append(disposition)
        if document is not None:
            candidates.append(document)
    result = WorkflowMigrationResult(migration_id, inventory.source_hash, tuple(candidates), tuple(dispositions))
    report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    latest = safe_generated_dir(root, ".paperops/workflow/migration") / "latest.json"
    latest.write_text(json.dumps({"migration_id": migration_id}, sort_keys=True) + "\n")
    return result


def _load_result(root: Path, migration_id: str) -> WorkflowMigrationResult:
    if re.fullmatch(r"WMIG-[0-9a-f]{16}", migration_id) is None:
        raise ValueError("invalid workflow migration id")
    payload = json.loads((safe_generated_dir(root, f".paperops/workflow/migration/{migration_id}") / "report.json").read_text())
    return WorkflowMigrationResult(payload["migration_id"], payload["source_hash"], tuple(payload["candidates"]), tuple(payload["dispositions"]))


def workflow_migration_status(root: Path) -> dict[str, Any]:
    manifest = read_manifest(root / ".pops/manifest.toml")
    workflow = as_table(manifest.get("workflow"))
    mode = workflow.get("mode", "legacy")
    if mode not in {"legacy", "shadow-compare", "v2-authoritative"}:
        raise ValueError("workflow authority mode is invalid")
    return {"mode": mode, "last_shadow_migration": workflow.get("last_shadow_migration", ""), "last_adopt_transaction": workflow.get("last_adopt_transaction", "")}


def plan_workflow_adoption(root: Path, migration_id: str):
    result = _load_result(root, migration_id)
    if inventory_legacy_workflow(root).source_hash != result.source_hash:
        raise ValueError("legacy workflow source drifted after shadow conversion")
    rows: list[dict[str, Any]] = []
    for document in result.candidates:
        identity = f"_paperops/model/issues/workflow/{document['id']}.yml"
        if (root / identity).exists():
            raise ValueError("workflow issue candidate conflicts with an existing record")
        rows.append(new_replacement(identity, document))
    index_identity = "_paperops/model/issues/index.yml"
    with SafeProjectReader(root) as reader:
        index_content, index_meta = reader.read_file(index_identity)
        manifest_content, manifest_meta = reader.read_file(".pops/manifest.toml")
    index = yaml.safe_load(index_content.decode())
    if not isinstance(index, dict) or not isinstance(index.get("records"), list):
        raise ValueError("Issue index is invalid")
    for document in result.candidates:
        identity = f"_paperops/model/issues/workflow/{document['id']}.yml"
        index["records"].append({"id": document["id"], "record_type": "workflow_issue", "document": identity, "expected_revision": 1, "expected_hash": semantic_hash(document)})
    if result.candidates:
        index["index_revision"] = int(index.get("index_revision", 0)) + 1
        rows.append(replacement(DocumentRef(index_identity, index_meta.content_hash, index), index))
    manifest = read_manifest(root / ".pops/manifest.toml")
    workflow = as_table(manifest.get("workflow"))
    workflow.update({"mode": "v2-authoritative", "last_shadow_migration": migration_id, "last_adopt_transaction": "pending"})
    manifest["workflow"] = workflow
    rows.append({"identity": ".pops/manifest.toml", "before_hash": manifest_meta.content_hash, "content": dumps_manifest_toml(manifest)})
    return persist_plan(root, "migration.adopt", rows)
