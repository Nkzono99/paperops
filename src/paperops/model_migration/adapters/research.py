"""Deterministic conversion of structured legacy research cards."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from ..legacy import LegacyCard, LegacySection, inventory_tree
from ..types import (
    CandidateDocument,
    InventoryItem,
    MigrationCandidate,
    MigrationFinding,
    MigrationInput,
)


_ROOTS = (
    Path("_paperops/claims/claims"),
    Path("_paperops/evidence/results"),
    Path("_paperops/evidence/figures"),
    Path("_paperops/evidence/sources"),
    Path("_paperops/claims/gates"),
)
_TYPE_ALIASES = {
    "claim": "claim",
    "result": "result",
    "figure": "figure",
    "source": "source",
    "scientific_gate": "scientific_gate",
}
_SCHEMAS = {
    "claim": "research-claim.schema.json",
    "result": "research-result.schema.json",
    "figure": "research-figure.schema.json",
    "source": "research-source.schema.json",
    "scientific_gate": "research-gate.schema.json",
}
_DIRECTORIES = {
    "claim": "claims",
    "result": "results",
    "figure": "figures",
    "source": "sources",
    "scientific_gate": "gates",
}
_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "claim": {
        "record_type": ("type",),
        "result_refs": ("evidence_cards", "Evidence/result cards"),
        "source_refs": ("source_cards", "Evidence/source cards"),
        "figure_refs": ("figure_cards", "Evidence/figure cards"),
        "manuscript_block_refs": ("manuscript_blocks", "Manuscript/block IDs"),
        "visual_obligation_refs": ("visual_obligations", "Visual obligations/visual_obligations"),
        "statement": ("section:主張",),
        "warrant": ("section:Warrant",),
        "not_claiming": ("Scope / Limitation/not claiming",),
        "abstract_conclusion_allowed": (
            "Manuscript/abstract / conclusion に使ってよいか",
        ),
        "upstream_feedback_refs": ("upstream_feedback",),
    },
    "result": {
        "record_type": ("type",),
        "observation": ("section:観察",),
        "unit_of_analysis": ("推定対象と単位/unit of analysis",),
        "denominator": ("推定対象と単位/denominator",),
        "independence_risk": ("推定対象と単位/independence risk",),
        "claim_refs": ("claim_links", "Claim への接続/支える claim"),
        "figure_refs": ("figure_links",),
        "manuscript_block_refs": ("manuscript_blocks",),
    },
    "figure": {
        "record_type": ("type",),
        "claim_refs": ("supports_claims",),
        "result_refs": ("uses_results",),
        "manuscript_block_refs": ("manuscript_blocks",),
        "visual_obligation_refs": ("satisfies_visual_obligations",),
        "manuscript_role": ("current_manuscript_role",),
    },
    "source": {
        "record_type": ("type",),
        "claim_refs": ("claim_links",),
        "public_provenance_refs": ("source_reach_refs",),
    },
    "scientific_gate": {
        "record_type": ("type",),
        "gate_decision": ("gate_status", "判定/decision"),
        "blocking_feedback_refs": ("blocking_feedback",),
        "analysis_request_refs": ("analysis_requests",),
    },
}
_PROSE_TARGETS = {
    ("claim", "主張"): "statement",
    ("claim", "Warrant"): "warrant",
    ("result", "観察"): "observation",
}
_HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _semantic_hash(value: Any, excluded: tuple[str, ...] = _HASH_EXCLUSIONS) -> str:
    normalized = copy.deepcopy(value)
    for pointer in excluded:
        current = normalized
        tokens = pointer.lstrip("/").split("/")
        for token in tokens[:-1]:
            if not isinstance(current, dict) or token not in current:
                current = None
                break
            current = current[token]
        if isinstance(current, dict):
            current.pop(tokens[-1], None)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _sections(card: LegacyCard) -> dict[str, LegacySection]:
    return {section.title: section for section in card.sections}


def _lookup(card: LegacyCard, locator: str) -> tuple[bool, Any, str]:
    value = card.frontmatter.get(locator)
    if value is not None:
        return True, value.value, value.pointer
    if locator.startswith("section:"):
        title = locator.removeprefix("section:")
        section = _sections(card).get(title)
        if section is not None and section.prose:
            return True, section.prose, section.pointer
        return False, None, ""
    if "/" in locator:
        title, name = locator.split("/", 1)
        section = _sections(card).get(title)
        if section is not None and name in section.definitions:
            field = section.definitions[name]
            return True, field.value, field.pointer
    prefixed = {
        key.removeprefix(locator + "."): field.value
        for key, field in card.frontmatter.items()
        if key.startswith(locator + ".")
    }
    if prefixed:
        return True, prefixed, f"/frontmatter/{locator}"
    return False, None, ""


def _required_fields(root: Path, record_type: str) -> tuple[str, ...]:
    path = root / "_paperops/defaults/schemas" / _SCHEMAS[record_type]
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = payload.get("required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError(f"managed schema has no usable required list: {path.name}")
    return tuple(required)


def _card_type(card: LegacyCard) -> str | None:
    value = card.frontmatter.get("record_type") or card.frontmatter.get("type")
    if value is None or not isinstance(value.value, str):
        return None
    return _TYPE_ALIASES.get(value.value)


def _card_id(card: LegacyCard) -> str:
    value = card.frontmatter.get("id")
    return value.value if value is not None and isinstance(value.value, str) else ""


def _confidential_pointers(card: LegacyCard) -> set[str]:
    return {
        finding.pointer
        for finding in card.findings
        if finding.code == "migration.confidential"
    }


def _known_sources(record_type: str, required: tuple[str, ...]) -> set[str]:
    aliases = _ALIASES[record_type]
    known = set(required) | {"id", "type", "created", "updated", "depends_on"}
    for values in aliases.values():
        known.update(locator for locator in values if not locator.startswith("section:"))
    return known


def _inventory_for(card: LegacyCard, record_type: str, required: tuple[str, ...]) -> list[InventoryItem]:
    identity = _card_id(card)
    confidential = _confidential_pointers(card)
    known = _known_sources(record_type, required)
    items: list[InventoryItem] = []
    for name, field in card.frontmatter.items():
        if field.pointer in confidential:
            disposition = "local-only"
            reason = "confidential value remains in the project-local legacy source"
            followup = ""
        elif name == "created":
            disposition = "deferred"
            reason = "legacy creation time remains in source provenance"
            followup = "P7"
        elif name in known or any(name.startswith(target + ".") for target in required):
            disposition = "mapped"
            reason = ""
            followup = ""
        else:
            disposition = "unsupported"
            reason = ""
            followup = ""
        items.append(
            InventoryItem(
                family=f"{record_type}.{name}",
                legacy_id=identity,
                source_path=card.source_path,
                pointer=field.pointer,
                source_hash=card.source_hash,
                disposition=disposition,
                target_id=identity if disposition == "mapped" else "",
                reason=reason,
                followup_phase=followup,
            )
        )
    for section in card.sections:
        target = _PROSE_TARGETS.get((record_type, section.title))
        if section.prose:
            disposition = "mapped" if target else "unsupported"
            items.append(
                InventoryItem(
                    family=f"{record_type}.section.{section.title}",
                    legacy_id=identity,
                    source_path=card.source_path,
                    pointer=section.pointer,
                    source_hash=card.source_hash,
                    disposition=disposition,
                    target_id=identity if disposition == "mapped" else "",
                )
            )
        for name, field in section.definitions.items():
            locator = f"{section.title}/{name}"
            disposition = "mapped" if locator in known else "unsupported"
            items.append(
                InventoryItem(
                    family=f"{record_type}.section.{section.title}.{name}",
                    legacy_id=identity,
                    source_path=card.source_path,
                    pointer=field.pointer,
                    source_hash=card.source_hash,
                    disposition=disposition,
                    target_id=identity if disposition == "mapped" else "",
                )
            )
    return items


def _materialize_card(
    card: LegacyCard,
    record_type: str,
    required: tuple[str, ...],
) -> tuple[dict[str, Any], list[MigrationFinding]]:
    document: dict[str, Any] = {}
    findings: list[MigrationFinding] = []
    aliases = _ALIASES[record_type]
    for target in required:
        locators = (target, *aliases.get(target, ()))
        found = False
        value: Any = None
        pointer = ""
        for locator in locators:
            found, value, pointer = _lookup(card, locator)
            if found:
                break
        if target == "schema_version" and not found:
            found, value = True, 1
        elif target == "record_type" and not found:
            found, value = True, record_type
        elif target == "dependencies" and not found:
            depends = card.frontmatter.get("depends_on")
            if depends is None or depends.value in ([], (), ""):
                found, value = True, []
        elif target == "approvals" and not found:
            found, value = True, []
        elif target == "extensions" and not found:
            found, value = True, {}
        elif target == "metadata" and not found:
            updated = card.frontmatter.get("updated")
            if updated is not None and isinstance(updated.value, str) and updated.value:
                found, value = True, {"updated_at": updated.value}
        if found:
            document[target] = value
        else:
            findings.append(
                MigrationFinding(
                    "migration.unresolved",
                    f"/{target}",
                    f"required `{target}` cannot be derived from an explicit legacy field",
                    source_path=card.source_path,
                )
            )
    if document.get("record_type") != record_type:
        findings.append(
            MigrationFinding(
                "migration.unresolved",
                "/record_type",
                "legacy record type does not match its deterministic adapter",
                source_path=card.source_path,
            )
        )
    return document, findings


class ResearchAdapter:
    adapter_version = 1

    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]:
        return self.materialize(migration_input).inventory

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate:
        root = migration_input.root.absolute()
        legacy = inventory_tree(root, migration_input.source_paths or _ROOTS)
        mapped_prose = {
            (card.source_path, section.pointer)
            for card in legacy.cards
            for section in card.sections
            if (_card_type(card), section.title) in _PROSE_TARGETS
        }
        findings = [
            finding
            for finding in legacy.findings
            if not (
                finding.code == "migration.unknown_field"
                and any(
                    finding.source_path == source
                    and finding.pointer.startswith(pointer + "/line-")
                    for source, pointer in mapped_prose
                )
            )
        ]
        documents: list[CandidateDocument] = []
        inventory: list[InventoryItem] = []
        materialized: list[tuple[LegacyCard, str, dict[str, Any], str]] = []
        seen: set[str] = set()
        for card in legacy.cards:
            record_type = _card_type(card)
            identity = _card_id(card)
            if record_type is None or not identity:
                findings.append(
                    MigrationFinding(
                        "migration.unresolved",
                        "/frontmatter/id",
                        "research card requires a known type and non-empty ID",
                        source_path=card.source_path,
                    )
                )
                continue
            try:
                required = _required_fields(root, record_type)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                findings.append(
                    MigrationFinding(
                        "migration.schema",
                        "/_paperops/defaults/schemas",
                        f"managed Research schema cannot be loaded: {error}",
                    )
                )
                continue
            inventory.extend(_inventory_for(card, record_type, required))
            document, card_findings = _materialize_card(card, record_type, required)
            findings.extend(card_findings)
            if identity in seen:
                continue
            seen.add(identity)
            relative = (
                f"_paperops/model/research/{_DIRECTORIES[record_type]}/{identity}.yml"
            )
            materialized.append((card, record_type, document, relative))

        by_id = {str(document.get("id", "")): document for _, _, document, _ in materialized}
        for _, record_type, document, _ in materialized:
            if record_type == "claim":
                gate = by_id.get(str(document.get("gate_id", "")))
                if gate is None or gate.get("claim_id") != document.get("id"):
                    findings.append(
                        MigrationFinding(
                            "migration.unresolved",
                            "/gate_id",
                            "claim and scientific gate must explicitly reference each other",
                        )
                    )
            if record_type == "result":
                quantities = document.get("quantity_contracts", [])
                if isinstance(quantities, list):
                    quantity_ids = [item.get("id") for item in quantities if isinstance(item, dict)]
                    if len(quantity_ids) != len(set(quantity_ids)):
                        findings.append(
                            MigrationFinding(
                                "migration.duplicate",
                                "/quantity_contracts",
                                "quantity contract IDs must be unique",
                            )
                        )

        records: list[dict[str, Any]] = []
        updated_values: list[str] = []
        for card, record_type, document, relative in sorted(
            materialized, key=lambda item: str(item[2].get("id", ""))
        ):
            identity = str(document.get("id", _card_id(card)))
            semantic_hash = _semantic_hash(document)
            documents.append(
                CandidateDocument(relative, identity, semantic_hash, _json_bytes(document))
            )
            revision = document.get("revision")
            if isinstance(revision, int):
                records.append(
                    {
                        "id": identity,
                        "record_type": record_type,
                        "document": relative,
                        "expected_revision": revision,
                        "expected_hash": semantic_hash,
                    }
                )
            metadata = document.get("metadata")
            if isinstance(metadata, dict) and isinstance(metadata.get("updated_at"), str):
                updated_values.append(metadata["updated_at"])
        index = {
            "model_name": "research",
            "schema_version": 1,
            "index_revision": 1,
            "records": records,
            "extensions": {},
            "metadata": {"updated_at": max(updated_values, default="")},
        }
        documents.append(
            CandidateDocument(
                "_paperops/model/research/index.yml",
                "research",
                _semantic_hash(index, ("/metadata/updated_at",)),
                _json_bytes(index),
            )
        )
        for item in inventory:
            if item.disposition == "unsupported":
                findings.append(
                    MigrationFinding(
                        "migration.unknown_field",
                        item.pointer,
                        "legacy field has no explicit Research Model mapping",
                        source_path=item.source_path,
                    )
                )
        return MigrationCandidate(
            model_name="research",
            documents=tuple(documents),
            inventory=tuple(inventory),
            findings=tuple(findings),
        )
