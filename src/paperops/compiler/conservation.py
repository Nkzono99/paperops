"""Pure occurrence-level conservation and mirror/privacy validation."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from .patches import WriterPatchResult
from .privacy import scan_private_material
from .types import CompileFinding, _freeze_json, _json_compatible


_SCIENTIFIC_KINDS = {
    "claim", "result", "figure", "citation", "quantity", "figure_label",
    "figure_reference", "predicted_marker", "analysis_request",
}
_DIAGNOSTIC_KINDS = {"placeholder", "authoring_intent"}


@dataclass(frozen=True)
class ConservationAnalysis:
    findings: tuple[CompileFinding, ...]
    dispositions: tuple[Mapping[str, Any], ...]
    introduced_references: tuple[Mapping[str, Any], ...]
    mirror_impacts: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        for name in ("dispositions", "introduced_references", "mirror_impacts"):
            object.__setattr__(
                self,
                name,
                tuple(_freeze_json(item) for item in getattr(self, name)),
            )


def _finding(code: str, pointer: str, message: str, severity: str = "error") -> CompileFinding:
    return CompileFinding(code, pointer, message, severity)


def _key(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _bindings(base: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(row.get("file_identity", "")), str(row.get("raw_block_id", ""))): row
        for row in base.get("bindings", ())
        if isinstance(row, Mapping)
    }


def _block_rows(files: object):
    if not isinstance(files, (list, tuple)):
        return
    for file_row in files:
        if not isinstance(file_row, Mapping):
            continue
        identity = str(file_row.get("identity", ""))
        for block in file_row.get("blocks", ()):
            if isinstance(block, Mapping):
                yield identity, block


def _occurrences(
    files: object,
    base: Mapping[str, Any],
) -> list[dict[str, object]]:
    binding_map = _bindings(base)
    rows: list[dict[str, object]] = []
    ordinal: Counter[tuple[str, str, str, str]] = Counter()
    present_bindings: set[tuple[str, str]] = set()
    for identity, block in _block_rows(files):
        raw_id = str(block.get("marker_id", ""))
        binding = binding_map.get((identity, raw_id), {})
        typed_id = str(binding.get("typed_block_id", ""))
        language = str(binding.get("language", ""))
        present_bindings.add((identity, raw_id))
        inventory = block.get("inventory", {})
        values: list[tuple[str, object]] = []
        if isinstance(inventory, Mapping):
            values.extend(("citation", item) for item in inventory.get("citation_keys", ()))
            values.extend(
                ("quantity", {key: item.get(key) for key in ("value", "denominator", "literal")})
                for item in inventory.get("quantities", ()) if isinstance(item, Mapping)
            )
            values.extend(("figure_label", item) for item in inventory.get("figure_labels", ()))
            values.extend(("figure_reference", item) for item in inventory.get("figure_references", ()))
            values.extend(
                ("predicted_marker", {key: item.get(key) for key in ("name", "body_hash", "analysis_request_ids")})
                for item in inventory.get("predicted_markers", ()) if isinstance(item, Mapping)
            )
            values.extend(("analysis_request", item) for item in inventory.get("analysis_request_ids", ()))
            values.extend(
                ("placeholder", item.get("literal"))
                for item in inventory.get("placeholders", ()) if isinstance(item, Mapping)
            )
            values.extend(
                ("authoring_intent", item.get("kind"))
                for item in inventory.get("authoring_intents", ()) if isinstance(item, Mapping)
            )
        for kind, value in values:
            semantic_key = _key(value)
            identity_key = (kind, semantic_key, identity, raw_id)
            current = ordinal[identity_key]
            ordinal[identity_key] += 1
            rows.append(
                {
                    "kind": kind,
                    "key": semantic_key,
                    "file": identity,
                    "raw_block_id": raw_id,
                    "typed_block_id": typed_id,
                    "language": language,
                    "ordinal": current,
                }
            )
    for (identity, raw_id), binding in binding_map.items():
        if (identity, raw_id) not in present_bindings:
            continue
        for field, kind in (
            ("claim_refs", "claim"),
            ("result_refs", "result"),
            ("figure_refs", "figure"),
        ):
            for value in binding.get(field, ()):
                semantic_key = _key(value)
                identity_key = (kind, semantic_key, identity, raw_id)
                current = ordinal[identity_key]
                ordinal[identity_key] += 1
                rows.append(
                    {
                        "kind": kind,
                        "key": semantic_key,
                        "file": identity,
                        "raw_block_id": raw_id,
                        "typed_block_id": str(binding.get("typed_block_id", "")),
                        "language": str(binding.get("language", "")),
                        "ordinal": current,
                    }
                )
    return sorted(
        rows,
        key=lambda row: (
            str(row["kind"]), str(row["key"]), str(row["file"]),
            str(row["raw_block_id"]), int(row["ordinal"]),
        ),
    )


def _identity(row: Mapping[str, object]) -> tuple[object, ...]:
    return tuple(
        row[field]
        for field in (
            "kind", "key", "file", "raw_block_id", "typed_block_id", "language", "ordinal"
        )
    )


def _endpoint(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "file": row["file"],
        "raw_block_id": row["raw_block_id"],
        "typed_block_id": row["typed_block_id"],
        "language": row["language"],
        "ordinal": row["ordinal"],
    }


def _known_citations(bundle: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for registry in bundle.get("global_context", {}).get("citation_registry", ())
        if isinstance(registry, Mapping)
        for key in registry.get("entry_keys", ())
    }


def _known_requests(bundle: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(item.get("id")): str(item.get("status"))
        for packet in bundle.get("writer_packets", ())
        if isinstance(packet, Mapping)
        for item in packet.get("payload", {}).get("predicted_result", {}).get("analysis_requests", ())
        if isinstance(item, Mapping)
    }


def analyze_patch(
    bundle: Mapping[str, Any],
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    patch: WriterPatchResult,
) -> ConservationAnalysis:
    base_rows = _occurrences(base.get("tex_files", ()), base)
    candidate_rows = _occurrences(candidate.get("tex_files", ()), base)
    candidate_by_identity = {_identity(row): row for row in candidate_rows}
    matched_candidate: set[tuple[object, ...]] = set()
    dispositions: list[dict[str, object]] = []
    findings: list[CompileFinding] = []
    introduced: list[dict[str, object]] = []
    change_by_block = {
        str(row.get("typed_block_id", "")): row
        for row in patch.changes
        if isinstance(row, Mapping)
    }
    binding_map = _bindings(base)

    unmatched_base: list[Mapping[str, object]] = []
    for row in base_rows:
        identity = _identity(row)
        if identity in candidate_by_identity:
            matched_candidate.add(identity)
            dispositions.append(
                {"kind": row["kind"], "key": row["key"], "disposition": "preserved", "from": _endpoint(row), "to": _endpoint(row)}
            )
        else:
            unmatched_base.append(row)
    unmatched_candidate = [
        row for row in candidate_rows if _identity(row) not in matched_candidate
    ]

    candidate_by_semantic: dict[tuple[object, object], list[Mapping[str, object]]] = defaultdict(list)
    for row in unmatched_candidate:
        candidate_by_semantic[(row["kind"], row["key"])].append(row)
    moved_candidate_ids: set[tuple[object, ...]] = set()
    still_removed: list[Mapping[str, object]] = []
    for row in unmatched_base:
        pool = candidate_by_semantic[(row["kind"], row["key"])]
        destination = next(
            (item for item in pool if _identity(item) not in moved_candidate_ids),
            None,
        )
        if destination is None:
            still_removed.append(row)
            continue
        moved_candidate_ids.add(_identity(destination))
        change = change_by_block.get(str(destination["typed_block_id"]), {})
        if change.get("operation") != "move":
            findings.append(
                _finding("write.replan_required", "/conservation", "reference movement requires current structural authority")
            )
        dispositions.append(
            {"kind": row["kind"], "key": row["key"], "disposition": "moved", "from": _endpoint(row), "to": _endpoint(destination)}
        )

    for row in still_removed:
        change = change_by_block.get(str(row["typed_block_id"]), {})
        authorized_cut = (
            change.get("operation") == "cut"
            and change.get("authorization") == "cut"
            and isinstance(change.get("model_revision"), int)
            and bool(change.get("model_hash"))
        )
        if row["kind"] in _DIAGNOSTIC_KINDS and change.get("operation") == "rewrite":
            disposition = "diagnostic_resolved"
        elif authorized_cut:
            disposition = "removed"
        else:
            disposition = "removed"
            findings.append(
                _finding("write.conservation_removed", "/conservation", "protected reference occurrence was removed without current cut authority")
            )
        dispositions.append(
            {"kind": row["kind"], "key": row["key"], "disposition": disposition, "from": _endpoint(row), "to": None}
        )

    known_citations = _known_citations(bundle)
    known_requests = _known_requests(bundle)
    for row in unmatched_candidate:
        if _identity(row) in moved_candidate_ids:
            continue
        kind = str(row["kind"])
        value = json.loads(str(row["key"]))
        binding = binding_map.get((str(row["file"]), str(row["raw_block_id"])), {})
        allowed = False
        if kind == "citation":
            allowed = value in known_citations and value in binding.get("citation_keys", ())
        elif kind == "analysis_request":
            allowed = value in known_requests and known_requests[value] in {"planned", "predicted", "running"}
        elif kind in _DIAGNOSTIC_KINDS:
            allowed = True
        if not allowed:
            findings.append(
                _finding("write.conservation_introduced", "/conservation", "introduced reference is not covered by current typed authority")
            )
        introduced.append(
            {"kind": kind, "key": row["key"], "destination": _endpoint(row), "covered": allowed}
        )

    custom = candidate.get("custom_citation_commands", ())
    if custom:
        findings.append(
            _finding("write.conservation_custom_citation_unsupported", "/citations", "custom citation commands require a hashed compile profile")
        )
    if candidate.get("privacy_violation"):
        findings.append(
            _finding("write.privacy_private_material", "/candidate", "candidate contains private material")
        )
    if candidate.get("terminology_violation"):
        findings.append(
            _finding("write.terminology_forbidden", "/candidate", "candidate contains internal or forbidden terminology")
        )

    predicted_names = {
        json.loads(str(row["key"])).get("name")
        for row in candidate_rows if row["kind"] == "predicted_marker"
    }
    if predicted_names and predicted_names != {
        "PREDICTED-RESULT", "SIM-REQUEST", "EXPECTATION-BASIS", "REPLACE-XX"
    }:
        findings.append(
            _finding("write.prediction_incomplete", "/prediction", "predicted material marker set is incomplete")
        )

    impacts: list[dict[str, object]] = []
    legacy_ledger_hash = next(
        (
            str(row.get("content_hash", ""))
            for row in base.get("files", ())
            if isinstance(row, Mapping)
            and str(row.get("identity", "")).endswith("block-ledger.yml")
        ),
        "",
    )
    languages_by_block: dict[str, set[str]] = defaultdict(set)
    for change in patch.changes:
        if not isinstance(change, Mapping):
            continue
        typed_id = str(change.get("typed_block_id", ""))
        for endpoint_name in ("from", "to"):
            endpoint = change.get(endpoint_name)
            if not isinstance(endpoint, Mapping):
                continue
            binding = binding_map.get((str(endpoint.get("file", "")), str(change.get("raw_block_id", ""))))
            if binding:
                languages_by_block[typed_id].add(str(binding.get("language", "")))
    for typed_id in sorted(languages_by_block):
        languages = sorted(languages_by_block[typed_id])
        status = "paired" if {"ja", "en"} <= set(languages) else "freshness_drift"
        impacts.append(
            {
                "typed_block_id": typed_id,
                "languages": languages,
                "status": status,
                "legacy_ledger_hash": legacy_ledger_hash,
            }
        )
        if status == "freshness_drift":
            findings.append(
                _finding("write.mirror_freshness_drift", "/mirror", "single-language edit requires mirror review", "warning")
            )

    for section in base.get("section_topology", ()):
        if not isinstance(section, Mapping):
            continue
        section_id = str(section.get("section_id", ""))
        for binding in section.get("move_bindings", ()):
            if not isinstance(binding, Mapping):
                continue
            dispositions.append(
                {
                    "kind": "argument_move",
                    "key": _key(
                        {
                            "move_id": binding.get("move_id"),
                            "role": binding.get("role"),
                            "section_id": section_id,
                        }
                    ),
                    "disposition": "preserved",
                    "from": None,
                    "to": None,
                }
            )

    if any(
        str(row.get("identity", "")).endswith("block-ledger.yml")
        for row in patch.target_files
    ):
        findings.append(
            _finding("write.mirror_ledger_modified", "/mirror", "mirror ledger must not be modified by Writer")
        )
    for hit in scan_private_material(
        {"dispositions": dispositions, "introduced": introduced, "mirror": impacts}
    ):
        del hit
        findings.append(
            _finding("write.privacy_private_material", "/report", "patch report contains private material")
        )
        break
    findings.sort(key=lambda item: (item.code, item.pointer, item.message, item.severity))
    dispositions.sort(key=lambda row: (str(row["kind"]), str(row["key"]), _key(row.get("from"))))
    introduced.sort(key=lambda row: (str(row["kind"]), str(row["key"]), _key(row["destination"])))
    return ConservationAnalysis(tuple(findings), tuple(dispositions), tuple(introduced), tuple(impacts))


def validate_patch(
    bundle: Mapping[str, Any],
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    patch: WriterPatchResult,
) -> tuple[CompileFinding, ...]:
    return analyze_patch(bundle, base, candidate, patch).findings


__all__ = ["ConservationAnalysis", "analyze_patch", "validate_patch"]
