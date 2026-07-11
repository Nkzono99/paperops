"""Structural Manuscript migration that never reads TeX prose into records."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from paperops.model_validation import run_model_validation

from ..types import CandidateDocument, InventoryItem, MigrationCandidate, MigrationFinding, MigrationInput


_MANIFEST = Path("_paperops/contracts/manuscript-migration.yml")


def _hash(value: Any, excluded: tuple[str, ...] = ("/approvals", "/metadata/updated_at")) -> str:
    normalized = copy.deepcopy(value)
    for pointer in excluded:
        current = normalized
        tokens = pointer.lstrip("/").split("/")
        for token in tokens[:-1]:
            current = current.get(token) if isinstance(current, dict) else None
        if isinstance(current, dict):
            current.pop(tokens[-1], None)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _contains_prose_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in {"prose", "tex", "content", "body"}
            or _contains_prose_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_prose_key(item) for item in value)
    return False


class ManuscriptAdapter:
    adapter_version = 1

    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]:
        return self.materialize(migration_input).inventory

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate:
        root = migration_input.root.absolute()
        path = root / _MANIFEST
        findings: list[MigrationFinding] = []
        try:
            raw = path.read_bytes()
            payload = yaml.safe_load(raw)
        except (OSError, yaml.YAMLError) as error:
            return MigrationCandidate(
                "manuscript", (), (),
                (MigrationFinding("migration.missing", "/manifest", f"structural manuscript manifest cannot be read: {error}", source_path=_MANIFEST.as_posix()),),
            )
        if not isinstance(payload, dict) or not isinstance(payload.get("sections"), list) or not isinstance(payload.get("blocks"), list):
            return MigrationCandidate("manuscript", (), (), (MigrationFinding("migration.unresolved", "/manifest", "manifest requires sections and blocks arrays", source_path=_MANIFEST.as_posix()),))
        if _contains_prose_key(payload):
            findings.append(MigrationFinding("migration.confidential", "/manifest", "TeX prose/content fields are forbidden in structural migration", source_path=_MANIFEST.as_posix()))
        sections = [item for item in payload["sections"] if isinstance(item, dict)]
        blocks = [item for item in payload["blocks"] if isinstance(item, dict)]
        block_ids = {str(item.get("id", "")): item for item in blocks}
        for section in sections:
            ordered = section.get("ordered_block_ids", [])
            actual = [
                str(item.get("id", ""))
                for item in sorted(
                    (block for block in blocks if block.get("section_id") == section.get("id")),
                    key=lambda item: item.get("position", 0),
                )
            ]
            if ordered != actual or any(identity not in block_ids for identity in ordered):
                findings.append(MigrationFinding("migration.unresolved", "/sections/ordered_block_ids", "section block order does not match block positions"))
            if section.get("status") in {"compiled", "drafted", "verified"} and not section.get("compiled_manifest_ref"):
                findings.append(MigrationFinding("migration.unresolved", "/compiled_manifest_ref", "compiled section requires explicit manifest lineage"))
        marker_check = payload.get("marker_check", True)
        tex_markers = ""
        if marker_check:
            for tex_path in sorted((root / "manuscript").rglob("*.tex")):
                tex_markers += "\n".join(
                    line for line in tex_path.read_text(errors="replace").splitlines() if line.lstrip().startswith("% block:")
                )
        research_refs: set[str] = set()
        for block_document in blocks:
            if block_document.get("status") in {"compiled", "drafted", "verified"} and not block_document.get("compiled_from"):
                findings.append(MigrationFinding("migration.unresolved", "/compiled_from", "compiled block requires explicit compiler lineage"))
            for key in ("ja_tex_block_id", "en_tex_block_id"):
                marker = str(block_document.get(key, ""))
                if marker_check and marker and marker not in tex_markers:
                    findings.append(MigrationFinding("migration.unresolved", f"/{key}", f"TeX block marker `{marker}` is missing"))
            research_refs.update(str(value) for key in ("claim_refs", "result_refs", "source_refs", "figure_refs") for value in block_document.get(key, []))
        research_refs.update(str(value) for section in sections for value in section.get("research_refs", []))
        if research_refs:
            validation = run_model_validation(root, "research", strict=True)
            try:
                research_index = yaml.safe_load(
                    (root / "_paperops/model/research/index.yml").read_text()
                )
                available = {
                    str(row.get("id", ""))
                    for row in research_index.get("records", [])
                    if isinstance(row, dict)
                }
            except (OSError, yaml.YAMLError, AttributeError):
                available = set()
            if not validation.ok or not research_refs.issubset(available):
                findings.append(MigrationFinding("approval.missing", "/research_refs", "referenced Research state is not strictly validated and approved"))

        records: list[dict[str, Any]] = []
        documents: list[CandidateDocument] = []
        inventory: list[InventoryItem] = []
        source_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
        for document in sorted([*sections, *blocks], key=lambda item: str(item.get("id", ""))):
            identity = str(document.get("id", ""))
            record_type = str(document.get("record_type", ""))
            directory = "sections" if record_type == "section" else "blocks"
            relative = f"_paperops/model/manuscript/{directory}/{identity}.yml"
            semantic_hash = _hash(document)
            documents.append(CandidateDocument(relative, identity, semantic_hash, _bytes(document)))
            if isinstance(document.get("revision"), int):
                records.append({"id": identity, "record_type": record_type, "document": relative, "expected_revision": document["revision"], "expected_hash": semantic_hash})
            inventory.append(InventoryItem(f"manuscript.{record_type}", identity, _MANIFEST.as_posix(), f"/{record_type}/{identity}", source_hash, "mapped", identity))
        index = {"model_name": "manuscript", "schema_version": 1, "index_revision": 1, "records": records, "extensions": {}, "metadata": {"updated_at": max((str(item.get("metadata", {}).get("updated_at", "")) for item in [*sections, *blocks]), default="")}}
        documents.append(CandidateDocument("_paperops/model/manuscript/index.yml", "manuscript", _hash(index, ("/metadata/updated_at",)), _bytes(index)))
        return MigrationCandidate("manuscript", tuple(documents), tuple(inventory), tuple(findings))
