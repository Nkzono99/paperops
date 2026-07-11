"""Deterministic Issue card migration with confidentiality filtering."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..legacy import LegacyCard, inventory_tree
from ..types import CandidateDocument, InventoryItem, MigrationCandidate, MigrationFinding, MigrationInput


_ROOTS = (
    Path("_paperops/review/feedback"),
    Path("_paperops/requests/analysis"),
    Path("_paperops/requests/writing"),
    Path("_paperops/review/responses"),
    Path("_paperops/review/rounds"),
)
_SCHEMAS = {
    "feedback": "issue-feedback.schema.json",
    "analysis_request": "issue-analysis-request.schema.json",
    "writing_request": "issue-writing-request.schema.json",
    "response": "issue-response.schema.json",
    "review_round": "issue-review-round.schema.json",
}
_DIRECTORIES = {
    "feedback": "feedback",
    "analysis_request": "analysis",
    "writing_request": "writing",
    "response": "responses",
    "review_round": "rounds",
}
_PRIVATE = re.compile(
    r"(?:^|\s)(?:/[^\s]+|\.\./[^\s]+|[A-Za-z]:[\\/][^\s]+|(?:token|password|secret|api[_-]?key)\s*[:=])",
    re.I,
)


def _unsafe(value: Any) -> bool:
    if isinstance(value, str):
        return bool(_PRIVATE.search(value)) or value.startswith(("file://", "ssh://", "sftp://"))
    if isinstance(value, dict):
        return any(_unsafe(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    return False


def _hash(value: Any, excluded: tuple[str, ...] = ("/approvals", "/metadata/updated_at")) -> str:
    normalized = copy.deepcopy(value)
    for pointer in excluded:
        current = normalized
        tokens = pointer.lstrip("/").split("/")
        for token in tokens[:-1]:
            current = current.get(token) if isinstance(current, dict) else None
        if isinstance(current, dict):
            current.pop(tokens[-1], None)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _type(card: LegacyCard) -> str:
    field = card.frontmatter.get("record_type") or card.frontmatter.get("type")
    return str(field.value) if field is not None else ""


class IssueAdapter:
    adapter_version = 1

    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]:
        return self.materialize(migration_input).inventory

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate:
        root = migration_input.root.absolute()
        legacy = inventory_tree(root, migration_input.source_paths or _ROOTS)
        findings = list(legacy.findings)
        documents: list[CandidateDocument] = []
        inventory: list[InventoryItem] = []
        records: list[dict[str, Any]] = []
        updated: list[str] = []
        seen: set[str] = set()
        for card in legacy.cards:
            record_type = _type(card)
            identity_field = card.frontmatter.get("id")
            identity = str(identity_field.value) if identity_field is not None else ""
            if record_type not in _SCHEMAS or not identity:
                findings.append(MigrationFinding("migration.unresolved", "/frontmatter", "Issue card requires a known type and ID", source_path=card.source_path))
                continue
            schema_path = root / "_paperops/defaults/schemas" / _SCHEMAS[record_type]
            try:
                schema = json.loads(schema_path.read_text())
                allowed = set(schema["properties"])
                required = set(schema["required"])
            except (OSError, KeyError, json.JSONDecodeError) as error:
                findings.append(MigrationFinding("migration.schema", "/schemas", f"Issue schema cannot be loaded: {error}"))
                continue
            document: dict[str, Any] = {"schema_version": 1, "record_type": record_type}
            confidential = {item.pointer for item in card.findings if item.code == "migration.confidential"}
            created = card.frontmatter.get("created")
            modified = card.frontmatter.get("updated")
            if created is not None and modified is not None:
                document["metadata"] = {"created_at": created.value, "updated_at": modified.value}
            for name, field in card.frontmatter.items():
                target = "record_type" if name == "type" else name
                if name in {"created", "updated"}:
                    target = "metadata"
                is_confidential = (
                    field.pointer in confidential
                    or name == "raw_reviewer_text"
                    or _unsafe(field.value)
                )
                if is_confidential:
                    disposition = "local-only"
                    reason = "confidential reviewer material remains only in the legacy source"
                    findings.append(MigrationFinding("migration.confidential", field.pointer, "confidential value was excluded from the Issue candidate", "warning", card.source_path))
                elif target in allowed:
                    disposition = "mapped"
                    reason = ""
                    if target not in {"metadata", "record_type", "schema_version"}:
                        document[target] = field.value
                else:
                    disposition = "unsupported"
                    reason = ""
                    findings.append(MigrationFinding("migration.unknown_field", field.pointer, "legacy Issue field has no explicit schema mapping", source_path=card.source_path))
                inventory.append(InventoryItem(f"issue.{record_type}.{name}", identity, card.source_path, field.pointer, card.source_hash, disposition, identity if disposition == "mapped" else "", reason))
            for missing in sorted(required - set(document)):
                findings.append(MigrationFinding("migration.unresolved", f"/{missing}", f"required Issue field `{missing}` is unavailable after confidentiality filtering", source_path=card.source_path))
            if identity in seen:
                continue
            seen.add(identity)
            relative = f"_paperops/model/issues/{_DIRECTORIES[record_type]}/{identity}.yml"
            semantic_hash = _hash(document)
            documents.append(CandidateDocument(relative, identity, semantic_hash, _bytes(document)))
            if isinstance(document.get("revision"), int):
                records.append({"id": identity, "record_type": record_type, "document": relative, "expected_revision": document["revision"], "expected_hash": semantic_hash})
            if isinstance(document.get("metadata"), dict):
                updated.append(str(document["metadata"].get("updated_at", "")))
        index = {"model_name": "issue", "schema_version": 1, "index_revision": 1, "records": sorted(records, key=lambda row: row["id"]), "extensions": {}, "metadata": {"updated_at": max(updated, default="")}}
        documents.sort(key=lambda item: item.object_id)
        documents.append(CandidateDocument("_paperops/model/issues/index.yml", "issue", _hash(index, ("/metadata/updated_at",)), _bytes(index)))
        unique = {(item.code, item.source_path, item.pointer, item.message, item.severity): item for item in findings}
        return MigrationCandidate("issue", tuple(documents), tuple(inventory), tuple(unique.values()))
