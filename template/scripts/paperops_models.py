"""Load PaperOps aggregate/index models and build a schema-clean object catalog."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit

from paperops_schema import (
    ModelFinding,
    RegistryEntry,
    SchemaRegistry,
    load_document,
    semantic_hash,
    validate_document_version,
    validate_extension_keys,
    validate_schema,
)


@dataclass(frozen=True)
class RecordDocument:
    model_name: str
    record_type: str
    path: Path
    document: dict[str, Any]
    object_id: str
    revision: int
    object_hash: str
    pointer: str


@dataclass(frozen=True)
class ModelDocument:
    entry: RegistryEntry
    path: Path
    document: Any | None
    schema_findings: tuple[ModelFinding, ...]
    records: tuple[RecordDocument, ...] = ()
    catalog_findings: tuple[ModelFinding, ...] = ()

    @property
    def schema_clean(self) -> bool:
        return (
            self.document is not None
            and not self.schema_findings
            and not any(
                finding.code.startswith(("schema.", "document.", "registry."))
                for finding in self.catalog_findings
            )
        )

    @property
    def findings(self) -> list[ModelFinding]:
        return [*self.schema_findings, *self.catalog_findings]


@dataclass(frozen=True)
class CatalogObject:
    object_id: str
    object_type: str
    model_name: str
    document: dict[str, Any]
    revision: int | None
    object_hash: str
    pointer: str


@dataclass(frozen=True)
class ObjectCatalog:
    objects: dict[str, CatalogObject]
    findings: tuple[ModelFinding, ...]


REFERENCE_CONTRACT_VERSION = 1
MODEL_OBJECT_TYPES: dict[str, frozenset[str]] = {
    "editorial": frozenset({"story", "move", "visual"}),
    "results_hierarchy": frozenset({"results_item"}),
    "research": frozenset({"claim", "result", "figure", "source", "scientific_gate"}),
    "manuscript": frozenset({"section", "block"}),
    "issue": frozenset(
        {"feedback", "analysis_request", "writing_request", "response", "review_round", "workflow_issue"}
    ),
    "publication": frozenset(),
}
REFERENCE_CONTRACTS: dict[str, dict[str, frozenset[str]]] = {
    "story": {"argument_move_ids": frozenset({"move"}), "result_order": frozenset({"results_item"})},
    "move": {"claim_ids": frozenset({"claim"}), "result_item_ids": frozenset({"results_item"})},
    "visual": {"claim_ids": frozenset({"claim"}), "figure_ids": frozenset({"figure"})},
    "claim": {"gate_id": frozenset({"scientific_gate"}), "result_refs": frozenset({"result"}), "figure_refs": frozenset({"figure"}), "source_refs": frozenset({"source"}), "manuscript_block_refs": frozenset({"block"}), "upstream_feedback_refs": frozenset({"feedback"}), "visual_obligation_refs": frozenset({"visual"})},
    "result": {"claim_refs": frozenset({"claim"}), "figure_refs": frozenset({"figure"}), "source_refs": frozenset({"source"}), "manuscript_block_refs": frozenset({"block"})},
    "figure": {"claim_refs": frozenset({"claim"}), "result_refs": frozenset({"result"}), "manuscript_block_refs": frozenset({"block"}), "visual_obligation_refs": frozenset({"visual"}), "claim_or_decision": frozenset({"claim"})},
    "source": {"claim_refs": frozenset({"claim"}), "manuscript_block_refs": frozenset({"block"})},
    "scientific_gate": {"claim_id": frozenset({"claim"}), "analysis_request_refs": frozenset({"analysis_request"}), "blocking_feedback_refs": frozenset({"feedback"}), "central_assumptions/*/guarded_claim_refs": frozenset({"claim"}), "central_assumptions/*/manuscript_block_refs": frozenset({"block"}), "external_validation_gates/*/blocking_claim_ref": frozenset({"claim"}), "external_validation_gates/*/route_ref": frozenset({"analysis_request"})},
    "section": {"editorial_move_refs": frozenset({"move"}), "move_bindings/*/move_id": frozenset({"move"}), "research_refs": frozenset({"claim", "result", "figure", "source", "scientific_gate"})},
    "block": {"section_id": frozenset({"section"}), "claim_refs": frozenset({"claim"}), "result_refs": frozenset({"result"}), "figure_refs": frozenset({"figure"}), "source_refs": frozenset({"source"})},
}
ISSUE_OBJECT_TYPES = frozenset(
    {"feedback", "analysis_request", "writing_request", "response", "review_round", "workflow_issue"}
)
ISSUE_REFERENCE_CONTRACTS: dict[str, dict[str, frozenset[str]]] = {
    record_type: {
        "review_round_ref": frozenset({"review_round"}),
        "related_issue_refs": ISSUE_OBJECT_TYPES,
        "related_block_refs": frozenset({"block"}),
    }
    for record_type in ISSUE_OBJECT_TYPES
}
ISSUE_REFERENCE_CONTRACTS["analysis_request"].update(
    {
        "requested_by": frozenset({"feedback"}),
        "related_claim_refs": frozenset({"claim"}),
        "related_result_refs": frozenset({"result"}),
        "manuscript_refs": frozenset({"section", "block"}),
        "prediction/basis_source_refs": frozenset({"source"}),
        "execution_provenance/result_refs": frozenset({"result"}),
        "execution_provenance/figure_refs": frozenset({"figure"}),
    }
)
ISSUE_REFERENCE_CONTRACTS["writing_request"].update(
    {
        "requested_by": frozenset({"feedback"}),
        "target_block_refs": frozenset({"block"}),
        "related_claim_refs": frozenset({"claim"}),
        "related_feedback_refs": frozenset({"feedback"}),
        "claim_evidence_constraints/claim_ref": frozenset({"claim"}),
    }
)
ISSUE_REFERENCE_CONTRACTS["response"].update(
    {
        "feedback_refs": frozenset({"feedback"}),
        "closure_audit/related_analysis_request_refs": frozenset({"analysis_request"}),
        "changed_claim_refs": frozenset({"claim"}),
        "changed_block_refs": frozenset({"block"}),
        "changed_gate_refs": frozenset({"scientific_gate"}),
        "changed_result_refs": frozenset({"result"}),
        "changed_source_refs": frozenset({"source"}),
        "changed_figure_refs": frozenset({"figure"}),
        "changed_request_refs": frozenset({"analysis_request", "writing_request"}),
    }
)
ISSUE_REFERENCE_CONTRACTS["review_round"].update(
    {
        "feedback_refs": frozenset({"feedback"}),
        "issue_refs": frozenset({"workflow_issue"}),
        "delegation_ledger/*/target_ref": frozenset().union(
            *MODEL_OBJECT_TYPES.values()
        ),
        "integration_decisions/*/feedback_ref": frozenset({"feedback"}),
    }
)
REFERENCE_CONTRACTS.update(ISSUE_REFERENCE_CONTRACTS)
ISSUE_TARGET_TYPES = {
    "claim": frozenset({"claim"}), "result": frozenset({"result"}),
    "figure": frozenset({"figure"}), "source": frozenset({"source"}),
    "scientific_gate": frozenset({"scientific_gate"}),
    "manuscript_section": frozenset({"section"}), "manuscript_block": frozenset({"block"}),
    "editorial_move": frozenset({"move"}), "results_item": frozenset({"results_item"}),
    "feedback": frozenset({"feedback"}), "analysis_request": frozenset({"analysis_request"}),
    "writing_request": frozenset({"writing_request"}), "response": frozenset({"response"}),
    "review_round": frozenset({"review_round"}),
    "workflow_issue": frozenset({"workflow_issue"}),
}


def validate_reference_contract_definition(
    registry: SchemaRegistry,
) -> list[ModelFinding]:
    """Ensure the versioned reference contract only names registered object types."""
    known_types = set().union(*MODEL_OBJECT_TYPES.values())
    findings: list[ModelFinding] = []
    if REFERENCE_CONTRACT_VERSION != 1:
        findings.append(
            ModelFinding(
                "registry.reference_contract",
                "/reference_contract_version",
                f"unsupported reference contract version `{REFERENCE_CONTRACT_VERSION}`",
            )
        )
    named_types = set(REFERENCE_CONTRACTS)
    named_types.update(
        target_type
        for fields in REFERENCE_CONTRACTS.values()
        for target_types in fields.values()
        for target_type in target_types
    )
    named_types.update(
        target_type
        for target_types in ISSUE_TARGET_TYPES.values()
        for target_type in target_types
    )
    for object_type in sorted(named_types - known_types):
        findings.append(
            ModelFinding(
                "registry.reference_contract",
                "/reference_contracts",
                f"object type `{object_type}` is not registered",
            )
        )
    complete_registry = set(MODEL_OBJECT_TYPES).issubset(registry.entries)
    for model_name, entry in registry.entries.items():
        expected_types = MODEL_OBJECT_TYPES.get(model_name)
        if (
            not complete_registry
            or expected_types is None
            or entry.document_kind != "index"
        ):
            continue
        actual_types = frozenset(entry.record_sets)
        if actual_types != expected_types:
            findings.append(
                ModelFinding(
                    "registry.reference_contract",
                    f"/models/{model_name}/record_sets",
                    f"registered types {sorted(actual_types)} do not match "
                    f"reference-contract types {sorted(expected_types)}",
                )
            )
    return findings


def _cross_reference_finding(
    catalog: ObjectCatalog,
    target_id: Any,
    expected_types: frozenset[str],
    pointer: str,
) -> ModelFinding | None:
    target = catalog.objects.get(target_id) if isinstance(target_id, str) else None
    if target is None:
        return ModelFinding("reference.dangling", pointer, f"target `{target_id}` does not exist")
    if target.object_type not in expected_types:
        return ModelFinding(
            "reference.type", pointer,
            f"target `{target_id}` has type `{target.object_type}`, expected {sorted(expected_types)}",
        )
    return None


def _contract_reference_values(
    document: Any,
    path: str,
) -> list[tuple[Any, str, str | None]]:
    """Return leaf reference values, pointers, and duplicate-list pointers."""
    leaves: list[tuple[Any, str, str | None]] = []

    def walk(value: Any, parts: list[str], pointer: str) -> None:
        if not parts:
            if isinstance(value, list):
                duplicate_pointer = (
                    pointer
                    if len({item for item in value if isinstance(item, str)})
                    != len(value)
                    else None
                )
                for index, item in enumerate(value):
                    leaves.append((item, f"{pointer}/{index}", duplicate_pointer))
            else:
                leaves.append((value, pointer, None))
            return
        part, *remaining = parts
        if part == "*":
            if isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, remaining, f"{pointer}/{index}")
            return
        if isinstance(value, dict) and part in value:
            walk(value[part], remaining, f"{pointer}/{part}")

    walk(document, path.split("/"), "")
    return leaves


def validate_cross_model_references(
    catalog: ObjectCatalog,
    *,
    defer_empty_editorial_research: bool = False,
) -> list[ModelFinding]:
    """Resolve version-1 field contracts against the schema-clean global catalog."""
    findings: list[ModelFinding] = []
    research_types = MODEL_OBJECT_TYPES["research"]
    for source in catalog.objects.values():
        contracts = REFERENCE_CONTRACTS.get(source.object_type, {})
        for field, expected_types in contracts.items():
            if (
                defer_empty_editorial_research
                and source.model_name == "editorial"
                and expected_types.issubset(research_types)
            ):
                continue
            duplicate_pointers: set[str] = set()
            for target_id, relative_pointer, duplicate_pointer in (
                _contract_reference_values(source.document, field)
            ):
                if duplicate_pointer is not None and duplicate_pointer not in duplicate_pointers:
                    duplicate_pointers.add(duplicate_pointer)
                    findings.append(ModelFinding(
                        "reference.cardinality", f"{source.pointer}{duplicate_pointer}",
                        f"reference field `{field}` must not contain duplicates",
                    ))
                pointer = f"{source.pointer}{relative_pointer}"
                finding = _cross_reference_finding(catalog, target_id, expected_types, pointer)
                if finding is not None:
                    findings.append(finding)
        targets = source.document.get("targets")
        if source.model_name == "issue" and isinstance(targets, list):
            for index, target_spec in enumerate(targets):
                if not isinstance(target_spec, dict):
                    continue
                kind = target_spec.get("kind")
                expected_types = ISSUE_TARGET_TYPES.get(kind) if isinstance(kind, str) else None
                if expected_types is None:
                    continue
                pointer = f"{source.pointer}/targets/{index}/id"
                finding = _cross_reference_finding(
                    catalog, target_spec.get("id"), expected_types, pointer,
                )
                if finding is not None:
                    findings.append(finding)
    return findings


def _dependency_entries(obj: CatalogObject) -> list[dict[str, Any]]:
    dependencies = obj.document.get("dependencies", [])
    return [entry for entry in dependencies if isinstance(entry, dict)] if isinstance(dependencies, list) else []


def _dependency_cycles(catalog: ObjectCatalog) -> set[str]:
    graph = {
        object_id: [
            entry.get("target_id") for entry in _dependency_entries(obj)
            if isinstance(entry.get("target_id"), str) and entry.get("target_id") in catalog.objects
        ]
        for object_id, obj in catalog.objects.items()
    }
    state: dict[str, int] = {object_id: 0 for object_id in graph}
    cyclic: set[str] = set()
    for start in graph:
        if state[start] != 0:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        trail: list[str] = []
        while stack:
            node, edge_index = stack[-1]
            if state[node] == 0:
                state[node] = 1
                trail.append(node)
            edges = graph[node]
            if edge_index >= len(edges):
                state[node] = 2
                stack.pop()
                if trail and trail[-1] == node:
                    trail.pop()
                continue
            target = edges[edge_index]
            stack[-1] = (node, edge_index + 1)
            if state.get(target) == 0:
                stack.append((target, 0))
            elif state.get(target) == 1:
                if target in trail:
                    cyclic.update(trail[trail.index(target):])
    return cyclic


def dependency_hash(object_id: str, catalog: ObjectCatalog) -> str:
    """Compute dependency-v1 from resolved current target identity snapshots."""
    obj = catalog.objects.get(object_id)
    if obj is None:
        raise ValueError(f"reference.dangling: /object-id: object `{object_id}` does not exist")
    if object_id in _dependency_cycles(catalog):
        raise ValueError(f"dependency.cycle: {obj.pointer}/dependencies: dependency cycle")
    resolved: list[dict[str, Any]] = []
    for entry in _dependency_entries(obj):
        target_id = entry.get("target_id")
        target = catalog.objects.get(target_id) if isinstance(target_id, str) else None
        if target is None:
            raise ValueError(f"reference.dangling: {obj.pointer}/dependencies: target `{target_id}` does not exist")
        resolved.append({
            "target_id": target.object_id,
            "relation": entry.get("relation"),
            "revision": target.revision,
            "hash": target.object_hash,
        })
    resolved.sort(key=lambda item: (str(item["target_id"]), str(item["relation"])))
    return semantic_hash({"profile": "dependency-v1", "dependencies": resolved})


def validate_dependency_state(catalog: ObjectCatalog) -> list[ModelFinding]:
    findings: list[ModelFinding] = []
    cyclic = _dependency_cycles(catalog)
    for object_id in sorted(cyclic):
        obj = catalog.objects[object_id]
        findings.append(ModelFinding("dependency.cycle", f"{obj.pointer}/dependencies", "dependency graph contains a cycle"))
    for obj in catalog.objects.values():
        seen: set[tuple[Any, Any]] = set()
        unresolved = False
        for index, entry in enumerate(_dependency_entries(obj)):
            target_id = entry.get("target_id")
            relation = entry.get("relation")
            key = (target_id, relation)
            if key in seen:
                findings.append(ModelFinding("reference.duplicate", f"{obj.pointer}/dependencies/{index}", "duplicate dependency target/relation"))
            seen.add(key)
            target = catalog.objects.get(target_id) if isinstance(target_id, str) else None
            if target is None:
                unresolved = True
                findings.append(ModelFinding("reference.dangling", f"{obj.pointer}/dependencies/{index}/target_id", f"dependency target `{target_id}` does not exist"))
                continue
            if target.revision is not None and entry.get("expected_revision") is None:
                findings.append(ModelFinding("dependency.missing_revision", f"{obj.pointer}/dependencies/{index}/expected_revision", "record dependency requires a revision snapshot"))
            if entry.get("expected_revision") is not None and entry.get("expected_revision") != target.revision:
                findings.append(ModelFinding("dependency.stale_revision", f"{obj.pointer}/dependencies/{index}/expected_revision", "dependency revision snapshot is stale"))
            if entry.get("expected_hash") != target.object_hash:
                findings.append(ModelFinding("dependency.stale_hash", f"{obj.pointer}/dependencies/{index}/expected_hash", "dependency semantic hash snapshot is stale"))
        if obj.object_id in cyclic or unresolved:
            continue
        expected = obj.document.get("last_verified_dependency_hash")
        if isinstance(expected, str) and expected and expected != dependency_hash(obj.object_id, catalog):
            findings.append(ModelFinding("dependency.stale", f"{obj.pointer}/last_verified_dependency_hash", "last verified dependency hash is stale"))
    return findings


def _issue_finding(
    code: str,
    obj: CatalogObject,
    suffix: str,
    message: str,
) -> ModelFinding:
    return ModelFinding(code, f"{obj.pointer}{suffix}", message)


def _issue_sensitive_text(value: str) -> bool:
    """Reject tracked secrets and machine-local paths, not ordinary prose."""
    stripped = value.strip()
    if not stripped:
        return False
    posix = PurePosixPath(stripped)
    windows = PureWindowsPath(stripped)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or re.search(r"(?i)(?:file|ssh|sftp)://\S+", stripped) is not None
    ):
        return True
    sensitive_patterns = (
        r"(?:^|[\s(\"'])/(?!/)[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)+",
        r"(?:^|[\s(\"'])/(?!/)[A-Za-z0-9._~-]+\.[A-Za-z0-9._~-]+",
        r"(?i)(?:^|[\s(\"'])/(?:home|users|tmp|var|etc|opt|srv|root|mnt|data|private|work|scratch|large[0-9]+)(?:/[A-Za-z0-9._~-]+)*",
        r"(?:^|[\s(\"'])(?:\.\./)+(?:[A-Za-z0-9._~-]+/)*[A-Za-z0-9._~-]+",
        r"(?i)(?:^|[\s(\"'])[A-Z]:[\\/](?:[^\\/\s]+[\\/])*[^\\/\s]+",
        r"(?i)authorization\s*:\s*(?:bearer|basic)\s+\S+",
        r"(?i)api[\s_-]*key\s*[:=]\s*\S+",
        r"(?i)(?:password|passwd|secret|credential|api[\s_-]*key)\s+is\s+"
        r"(?!(?:not|described|discussed|mentioned|documented|stored|omitted|redacted)\b)\S+",
        r"(?i)(?:access|auth|bearer|refresh|session|id)[\s_-]*token\s*(?:is|:|=)\s*\S+",
        r"(?i)token\s*[:=]\s*\S+",
        r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"(?i)(?:password|passwd|secret|credential)\s*[:=]\s*\S+",
    )
    if any(re.search(pattern, stripped) is not None for pattern in sensitive_patterns):
        return True
    return False


def _walk_issue_strings(value: Any, pointer: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield pointer, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_issue_strings(item, f"{pointer}/{index}")
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                escaped = key.replace("~", "~0").replace("/", "~1")
                yield from _walk_issue_strings(item, f"{pointer}/{escaped}")


def validate_issue_semantics(catalog: ObjectCatalog) -> list[ModelFinding]:
    """Validate Issue privacy, analysis lifecycle, and response closure."""
    findings: list[ModelFinding] = []
    issues = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "issue"
    }

    for obj in issues.values():
        extensions = obj.document.get("extensions")
        if isinstance(extensions, dict):
            for extension_finding in validate_extension_keys(extensions):
                findings.append(
                    _issue_finding(
                        extension_finding.code,
                        obj,
                        f"/extensions{extension_finding.pointer}",
                        extension_finding.message,
                    )
                )
            for key in extensions:
                if isinstance(key, str) and _sensitive_extension_key(key):
                    findings.append(
                        _issue_finding(
                            "semantic.extension",
                            obj,
                            f"/extensions/{key.replace('~', '~0').replace('/', '~1')}",
                            "extension may not store credentials or local paths",
                        )
                    )
        for pointer, value in _walk_issue_strings(obj.document):
            if _issue_sensitive_text(value):
                findings.append(
                    _issue_finding(
                        "semantic.confidentiality",
                        obj,
                        pointer,
                        "Issue state may contain only public summaries and opaque local-reference IDs",
                    )
                )

        if obj.object_type == "workflow_issue" and obj.document.get("status") == "closed":
            impacts = obj.document.get("impacts", [])
            unresolved = [
                row for row in impacts
                if not isinstance(row, dict) or row.get("state") not in {"resolved", "waived"}
            ] if isinstance(impacts, list) else [impacts]
            if unresolved:
                findings.append(_issue_finding("semantic.workflow_issue_closure", obj, "/impacts", "closed workflow issue cannot retain open impacts"))
            blockers = obj.document.get("blocking_dependency_refs", [])
            if not isinstance(blockers, list) or blockers:
                findings.append(_issue_finding("semantic.workflow_issue_closure", obj, "/blocking_dependency_refs", "closed workflow issue cannot retain blocking dependencies"))
            closure = obj.document.get("closure")
            if not isinstance(closure, dict) or closure.get("decision") != "closed" or not closure.get("verification_refs"):
                findings.append(_issue_finding("semantic.workflow_issue_verification", obj, "/closure", "closed workflow issue requires current verification references"))
            if isinstance(impacts, list) and any(isinstance(row, dict) and row.get("state") == "waived" for row in impacts):
                approvals = obj.document.get("approvals", [])
                current_waiver = any(
                    isinstance(approval, dict)
                    and approval.get("kind") == "waiver"
                    and approval.get("decision") == "approved"
                    and approval.get("object_revision") == obj.revision
                    and approval.get("object_hash") == obj.object_hash
                    for approval in approvals
                ) if isinstance(approvals, list) else False
                if not current_waiver:
                    findings.append(_issue_finding("approval.missing", obj, "/approvals", "waived impact requires a current owner-local waiver approval"))

        if obj.object_type != "analysis_request":
            continue
        status = obj.document.get("status")
        provenance = obj.document.get("execution_provenance")
        if status in {"executed", "reconciled"}:
            output_refs: list[Any] = []
            if isinstance(provenance, dict):
                for field in ("artifact_refs", "result_refs", "figure_refs"):
                    values = provenance.get(field)
                    if isinstance(values, list):
                        output_refs.extend(values)
            if not output_refs:
                findings.append(
                    _issue_finding(
                        "semantic.execution_outputs",
                        obj,
                        "/execution_provenance",
                        "executed analysis requires artifact, result, or figure output refs",
                    )
                )
        if status == "reconciled":
            reconciliation = obj.document.get("reconciliation")
            complete = (
                isinstance(reconciliation, dict)
                and bool(reconciliation.get("observed_result"))
                and reconciliation.get("outcome") in {"confirmed", "refuted", "mixed", "null"}
                and reconciliation.get("gate_rerun") in {"completed", "not_required"}
                and reconciliation.get("human_signoff") in {"approved", "rejected"}
            )
            if not complete:
                findings.append(
                    _issue_finding(
                        "semantic.reconciliation",
                        obj,
                        "/reconciliation",
                        "reconciled analysis requires observed reconciliation and human signoff",
                    )
                )
        prediction = obj.document.get("prediction")
        if (
            isinstance(prediction, dict)
            and prediction.get("state") == "predicted"
            and status not in {"reconciled", "abandoned"}
        ):
            findings.append(
                ModelFinding(
                    "semantic.predicted_unresolved",
                    f"{obj.pointer}/prediction/state",
                    "predicted analysis remains unresolved until reconciliation or abandonment",
                    severity="warning",
                )
            )

    for obj in issues.values():
        if obj.object_type != "response" or obj.document.get("status") != "closed":
            continue
        closure_criteria = obj.document.get("closure_criteria", [])
        if not isinstance(closure_criteria, list) or not closure_criteria:
            findings.append(
                _issue_finding(
                    "semantic.response_closure",
                    obj,
                    "/closure_criteria",
                    "closed response requires non-empty closure criteria",
                )
            )
        blockers = obj.document.get("blocking_dependency_refs", [])
        if not isinstance(blockers, list) or blockers:
            findings.append(
                _issue_finding(
                    "semantic.response_closure",
                    obj,
                    "/blocking_dependency_refs",
                    "closed response cannot retain blocking dependency refs",
                )
            )
        audit = obj.document.get("closure_audit")
        if not isinstance(audit, dict):
            continue
        if audit.get("closure_status") != "closed" or audit.get("criteria_met") is not True:
            findings.append(
                _issue_finding(
                    "semantic.response_closure",
                    obj,
                    "/closure_audit",
                    "closed response requires a closed audit with all criteria met",
                )
            )
        request_refs = audit.get("related_analysis_request_refs", [])
        if isinstance(request_refs, list):
            for index, request_id in enumerate(request_refs):
                request = issues.get(request_id) if isinstance(request_id, str) else None
                if (
                    request is not None
                    and request.object_type == "analysis_request"
                    and request.document.get("status") not in {"reconciled", "abandoned"}
                ):
                    findings.append(
                        _issue_finding(
                            "semantic.response_open_request",
                            obj,
                            f"/closure_audit/related_analysis_request_refs/{index}",
                            f"analysis request `{request_id}` is still open",
                        )
                    )
        dependencies = obj.document.get("dependencies", [])
        if isinstance(dependencies, list):
            for index, dependency in enumerate(dependencies):
                request_id = dependency.get("target_id") if isinstance(dependency, dict) else None
                request = issues.get(request_id) if isinstance(request_id, str) else None
                if (
                    request is not None
                    and request.object_type == "analysis_request"
                    and request.document.get("status") not in {"reconciled", "abandoned"}
                ):
                    findings.append(
                        _issue_finding(
                            "semantic.response_open_request",
                            obj,
                            f"/dependencies/{index}/target_id",
                            f"analysis request `{request_id}` is still open",
                        )
                    )
        human_refs = audit.get("open_human_decision_refs", [])
        if isinstance(human_refs, list) and human_refs:
            findings.append(
                _issue_finding(
                    "semantic.response_human_decision",
                    obj,
                    "/closure_audit/open_human_decision_refs",
                    "closed response cannot retain an open human decision",
                )
            )
        scope_approval_refs = audit.get("scope_change_approval_refs", [])
        if obj.document.get("scope_changed") is True:
            referenced = set(scope_approval_refs) if isinstance(scope_approval_refs, list) else set()
            approvals = obj.document.get("approvals", [])
            history = [
                approval
                for approval in approvals
                if isinstance(approval, dict)
                and approval.get("approval_id") in referenced
                and approval.get("kind") == "scope_expansion"
            ] if isinstance(approvals, list) else []
            current = [
                approval
                for approval in history
                if approval.get("object_revision") == obj.revision
                and approval.get("object_hash") == obj.object_hash
            ]
            if history and not current:
                findings.append(
                    _issue_finding(
                        "approval.stale",
                        obj,
                        "/closure_audit/scope_change_approval_refs",
                        "scope expansion approval does not match the current response revision/hash",
                    )
                )
            elif not current or current[-1].get("decision") != "approved":
                findings.append(
                    _issue_finding(
                        "approval.missing",
                        obj,
                        "/closure_audit/scope_change_approval_refs",
                        "closed response with changed claim scope requires current human scope approval",
                    )
                )
    return findings


def _research_finding(code: str, obj: CatalogObject, suffix: str, message: str) -> ModelFinding:
    return ModelFinding(code, f"{obj.pointer}{suffix}", message)


def validate_research_semantics(catalog: ObjectCatalog) -> list[ModelFinding]:
    """Validate Research gate readiness, approvals, quantities, and provenance."""
    findings: list[ModelFinding] = []
    research = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "research"
    }
    quantity_ids: dict[str, tuple[CatalogObject, int]] = {}
    for obj in research.values():
        document = obj.document
        extensions = document.get("extensions")
        if isinstance(extensions, dict):
            for extension_finding in validate_extension_keys(extensions):
                findings.append(
                    _research_finding(
                        extension_finding.code,
                        obj,
                        f"/extensions{extension_finding.pointer}",
                        extension_finding.message,
                    )
                )
            for key in extensions:
                if isinstance(key, str) and _sensitive_extension_key(key):
                    findings.append(
                        _research_finding(
                            "semantic.extension",
                            obj,
                            f"/extensions/{key.replace('~', '~0').replace('/', '~1')}",
                            f"extension key `{key}` may not store credential or local-path state",
                        )
                    )
        if obj.object_type == "result":
            quantities = document.get("quantity_contracts", [])
            if isinstance(quantities, list):
                for index, quantity in enumerate(quantities):
                    quantity_id = quantity.get("id") if isinstance(quantity, dict) else None
                    if not isinstance(quantity_id, str):
                        continue
                    previous = quantity_ids.get(quantity_id)
                    if previous is not None:
                        findings.append(
                            _research_finding(
                                "reference.duplicate",
                                obj,
                                f"/quantity_contracts/{index}/id",
                                f"duplicate ID `{quantity_id}`",
                            )
                        )
                    else:
                        quantity_ids[quantity_id] = (obj, index)
            provenance = document.get("artifact_provenance_ids", [])
            _validate_public_provenance(obj, provenance, "/artifact_provenance_ids", findings)
        elif obj.object_type == "source":
            provenance = document.get("public_provenance_refs", [])
            _validate_public_provenance(obj, provenance, "/public_provenance_refs", findings)

    for claim in (obj for obj in research.values() if obj.object_type == "claim"):
        gate_id = claim.document.get("gate_id")
        paired_gate = research.get(gate_id) if isinstance(gate_id, str) else None
        if paired_gate is None or paired_gate.object_type != "scientific_gate":
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    claim,
                    "/gate_id",
                    f"claim gate `{gate_id}` is not a Research scientific gate",
                )
            )

    for gate in (obj for obj in research.values() if obj.object_type == "scientific_gate"):
        claim_id = gate.document.get("claim_id")
        claim = research.get(claim_id) if isinstance(claim_id, str) else None
        if claim is None or claim.object_type != "claim":
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    gate,
                    "/claim_id",
                    f"gate claim `{claim_id}` is not a Research claim",
                )
            )
            continue
        if (
            claim.document.get("gate_id") != gate.object_id
            or claim.document.get("gate_status") != gate.document.get("gate_decision")
        ):
            findings.append(
                _research_finding(
                    "semantic.gate_pair",
                    gate,
                    "/claim_id",
                    f"gate `{gate.object_id}` and claim `{claim.object_id}` do not agree",
                )
            )
        if gate.document.get("gate_decision") != "ready_to_write":
            continue
        if claim.document.get("status") != "approved":
            findings.append(
                _research_finding(
                    "semantic.claim_not_writable",
                    gate,
                    "/gate_decision",
                    f"claim `{claim.object_id}` is not approved",
                )
            )
        approval_state = _scientific_approval_state(claim)
        if approval_state == "missing":
            findings.append(
                _research_finding(
                    "approval.missing",
                    claim,
                    "/approvals",
                    "current scientific_scope approval is required",
                )
            )
        elif approval_state == "stale":
            findings.append(
                _research_finding(
                    "approval.stale",
                    claim,
                    "/approvals",
                    "scientific_scope approval does not match current revision/hash",
                )
            )
        elif approval_state == "rejected":
            findings.append(
                _research_finding(
                    "approval.missing",
                    claim,
                    "/approvals",
                    "latest current scientific_scope decision is not approved",
                )
            )
    return findings


def _manuscript_finding(
    code: str,
    obj: CatalogObject,
    suffix: str,
    message: str,
) -> ModelFinding:
    return ModelFinding(code, f"{obj.pointer}{suffix}", message)


def _scientific_approval_state(claim: CatalogObject) -> str:
    approvals = claim.document.get("approvals", [])
    history = [
        approval
        for approval in approvals
        if isinstance(approval, dict)
        and approval.get("kind") == "scientific_scope"
    ] if isinstance(approvals, list) else []
    current = [
        approval
        for approval in history
        if approval.get("object_revision") == claim.revision
        and approval.get("object_hash") == claim.object_hash
    ]
    if not history:
        return "missing"
    if not current:
        return "stale"
    if current[-1].get("decision") != "approved":
        return "rejected"
    return "approved"


def _editorial_plan_approval_state(section: CatalogObject) -> str:
    approvals = section.document.get("approvals", [])
    history = [
        approval
        for approval in approvals
        if isinstance(approval, dict)
        and approval.get("kind") == "editorial_choice"
    ] if isinstance(approvals, list) else []
    current = [
        approval
        for approval in history
        if approval.get("object_revision") == section.revision
        and approval.get("object_hash") == section.object_hash
    ]
    if not history:
        return "missing"
    if not current:
        return "stale"
    if current[-1].get("decision") != "approved":
        return "rejected"
    return "approved"


def _section_move_bindings(
    section: CatalogObject,
) -> list[tuple[int, dict[str, Any]]]:
    bindings = section.document.get("move_bindings")
    if not isinstance(bindings, list):
        return []
    return [
        (index, binding)
        for index, binding in enumerate(bindings)
        if isinstance(binding, dict)
    ]


def _move_primary_placements(
    sections: Iterable[CatalogObject],
) -> dict[str, list[tuple[CatalogObject, int]]]:
    placements: dict[str, list[tuple[CatalogObject, int]]] = {}
    for section in sections:
        for index, binding in _section_move_bindings(section):
            move_id = binding.get("move_id")
            if (
                isinstance(move_id, str)
                and binding.get("role") == "primary"
            ):
                placements.setdefault(move_id, []).append((section, index))
    return placements


def _validate_move_binding_projection(
    sections: Iterable[CatalogObject],
) -> list[ModelFinding]:
    findings: list[ModelFinding] = []
    for section in sorted(sections, key=lambda item: item.object_id):
        bindings = section.document.get("move_bindings")
        if not isinstance(bindings, list):
            continue
        binding_ids = [
            binding.get("move_id")
            for binding in bindings
            if isinstance(binding, dict)
        ]
        editorial_refs = section.document.get("editorial_move_refs", [])
        if not isinstance(editorial_refs, list) or binding_ids != editorial_refs:
            findings.append(
                _manuscript_finding(
                    "compile.move_binding_mismatch",
                    section,
                    "/move_bindings",
                    "move binding IDs must exactly project editorial_move_refs order",
                )
            )
    return findings


def validate_manuscript_semantics(catalog: ObjectCatalog) -> list[ModelFinding]:
    """Validate Manuscript structure and its Research write-readiness boundary."""
    findings: list[ModelFinding] = []
    manuscript = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "manuscript"
    }
    sections = {
        object_id: obj
        for object_id, obj in manuscript.items()
        if obj.object_type == "section"
    }
    blocks = {
        object_id: obj
        for object_id, obj in manuscript.items()
        if obj.object_type == "block"
    }
    research = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "research"
    }
    findings.extend(_validate_move_binding_projection(sections.values()))

    for obj in manuscript.values():
        extensions = obj.document.get("extensions")
        if isinstance(extensions, dict):
            for finding in validate_extension_keys(extensions):
                findings.append(
                    _manuscript_finding(
                        finding.code,
                        obj,
                        f"/extensions{finding.pointer}",
                        finding.message,
                    )
                )
        has_block_lineage = (
            obj.object_type == "block"
            and obj.document.get("compiled_from") is not None
        )
        requires_compiled_state = (
            obj.document.get("status") in {
                "compiled", "drafted", "verified", "stale", "removed",
            }
            or has_block_lineage
        )
        if (
            requires_compiled_state
            and obj.object_type == "section"
            and not obj.document.get("compiled_manifest_ref")
        ):
            findings.append(
                _manuscript_finding(
                    "semantic.compiled_from",
                    obj,
                    "/compiled_manifest_ref",
                    "compiled section state requires a compiled manifest reference",
                )
            )
        dependency_hash = obj.document.get("dependency_hash")
        verified_hash = obj.document.get("last_verified_dependency_hash")
        if requires_compiled_state and not dependency_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.missing",
                    obj,
                    "/dependency_hash",
                    "compiled state requires a current dependency hash",
                )
            )
        if requires_compiled_state and not verified_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.missing",
                    obj,
                    "/last_verified_dependency_hash",
                    "compiled state requires a last verified dependency hash",
                )
            )
        if dependency_hash and verified_hash and dependency_hash != verified_hash:
            findings.append(
                _manuscript_finding(
                    "dependency.stale",
                    obj,
                    "/last_verified_dependency_hash",
                    "verified dependency hash does not match the current dependency hash",
                )
            )

    for section in sections.values():
        ordered_ids = section.document.get("ordered_block_ids", [])
        if not isinstance(ordered_ids, list):
            continue
        if len(set(ordered_ids)) != len(ordered_ids):
            findings.append(
                _manuscript_finding(
                    "semantic.block_order",
                    section,
                    "/ordered_block_ids",
                    "ordered block IDs must be unique",
                )
            )
        for expected_position, block_id in enumerate(ordered_ids, start=1):
            block = blocks.get(block_id) if isinstance(block_id, str) else None
            if block is None or block.document.get("section_id") != section.object_id:
                findings.append(
                    _manuscript_finding(
                        "semantic.section_membership",
                        section,
                        f"/ordered_block_ids/{expected_position - 1}",
                        f"block `{block_id}` is not a member of section `{section.object_id}`",
                    )
                )
                continue
            if block.document.get("position") != expected_position:
                findings.append(
                    _manuscript_finding(
                        "semantic.block_order",
                        block,
                        "/position",
                        f"block position must be {expected_position} in its section",
                    )
                )

    for block in blocks.values():
        section_id = block.document.get("section_id")
        section = sections.get(section_id) if isinstance(section_id, str) else None
        ordered_ids = section.document.get("ordered_block_ids", []) if section else []
        if section is None or block.object_id not in ordered_ids:
            findings.append(
                _manuscript_finding(
                    "semantic.section_membership",
                    block,
                    "/section_id",
                    f"block `{block.object_id}` is not listed by its section `{section_id}`",
                )
            )

        allowed_operations = block.document.get("allowed_operations", [])
        if block.document.get("operation") not in allowed_operations:
            findings.append(
                _manuscript_finding(
                    "semantic.operation",
                    block,
                    "/operation",
                    "block operation must be included in allowed_operations",
                )
            )

        compiled_from = block.document.get("compiled_from")
        requires_compilation = block.document.get("status") in {
            "compiled", "drafted", "verified", "stale", "removed",
        }
        if compiled_from is None and not requires_compilation:
            continue
        complete_compilation = (
            isinstance(compiled_from, dict)
            and isinstance(compiled_from.get("compiler_version"), str)
            and bool(compiled_from.get("compiler_version"))
            and isinstance(compiled_from.get("schema_versions"), dict)
            and bool(compiled_from.get("schema_versions"))
            and isinstance(compiled_from.get("input_ids"), list)
            and bool(compiled_from.get("input_ids"))
            and isinstance(compiled_from.get("input_hashes"), list)
            and len(compiled_from.get("input_ids"))
            == len(compiled_from.get("input_hashes"))
        )
        if not complete_compilation:
            findings.append(
                _manuscript_finding(
                    "semantic.compiled_from",
                    block,
                    "/compiled_from",
                    "compiled blocks require complete compiler, schema, input ID, and input hash provenance",
                )
            )

        for index, claim_id in enumerate(block.document.get("claim_refs", [])):
            claim = research.get(claim_id) if isinstance(claim_id, str) else None
            if claim is None or claim.object_type != "claim":
                findings.append(
                    _manuscript_finding(
                        "reference.dangling",
                        block,
                        f"/claim_refs/{index}",
                        f"Research claim `{claim_id}` is not present",
                    )
                )
                continue
            approval_state = _scientific_approval_state(claim)
            if approval_state != "approved":
                code = "approval.stale" if approval_state == "stale" else "approval.missing"
                findings.append(
                    _manuscript_finding(
                        code,
                        block,
                        f"/claim_refs/{index}",
                        f"claim `{claim_id}` lacks a current approved scientific_scope decision",
                    )
                )
            gate_id = claim.document.get("gate_id")
            gate = research.get(gate_id) if isinstance(gate_id, str) else None
            if (
                claim.document.get("status") != "approved"
                or claim.document.get("gate_status") != "ready_to_write"
                or gate is None
                or gate.object_type != "scientific_gate"
                or gate.document.get("claim_id") != claim.object_id
                or gate.document.get("gate_decision") != "ready_to_write"
            ):
                findings.append(
                    _manuscript_finding(
                        "semantic.claim_not_writable",
                        block,
                        f"/claim_refs/{index}",
                        f"claim `{claim_id}` has not passed its ready_to_write gate",
                    )
                )

        reference_fields = {
            "result_refs": "result",
            "source_refs": "source",
            "figure_refs": "figure",
        }
        for field, expected_type in reference_fields.items():
            for index, object_id in enumerate(block.document.get(field, [])):
                target = research.get(object_id) if isinstance(object_id, str) else None
                if target is None or target.object_type != expected_type:
                    findings.append(
                        _manuscript_finding(
                            "reference.dangling",
                            block,
                            f"/{field}/{index}",
                            f"Research {expected_type} `{object_id}` is not present",
                        )
                    )
    return findings


def validate_manuscript_compile_readiness(
    catalog: ObjectCatalog,
    section_ids: Iterable[str] | None = None,
) -> list[ModelFinding]:
    """Validate the additive Manuscript requirements used only by P3 compile."""
    sections = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "manuscript" and obj.object_type == "section"
    }
    blocks = {
        object_id: obj
        for object_id, obj in catalog.objects.items()
        if obj.model_name == "manuscript" and obj.object_type == "block"
    }
    findings: list[ModelFinding] = []
    if section_ids is None:
        selected = sorted(
            (
                section
                for section in sections.values()
                if section.document.get("status") != "unplanned"
            ),
            key=lambda item: item.object_id,
        )
    else:
        requested = {section_ids} if isinstance(section_ids, str) else set(section_ids)
        for missing_id in sorted(requested - set(sections)):
            findings.append(
                ModelFinding(
                    "compile.target_missing",
                    "/section_ids",
                    f"requested Manuscript section `{missing_id}` is not present",
                )
            )
        selected = sorted(
            (
                section
                for object_id, section in sections.items()
                if object_id in requested
            ),
            key=lambda item: item.object_id,
        )

    if not selected:
        return findings

    findings.extend(_validate_move_binding_projection(selected))
    primary_placements = _move_primary_placements(sections.values())

    canonical_move_references: dict[str, tuple[CatalogObject, int]] = {}
    for section in selected:
        editorial_refs = section.document.get("editorial_move_refs", [])
        if not isinstance(editorial_refs, list):
            continue
        for index, move_id in enumerate(editorial_refs):
            if isinstance(move_id, str):
                canonical_move_references.setdefault(move_id, (section, index))

    for move_id in sorted(canonical_move_references):
        placements = primary_placements.get(move_id, [])
        if len(placements) == 1:
            continue
        section, index = canonical_move_references[move_id]
        findings.append(
            _manuscript_finding(
                "compile.move_primary",
                section,
                f"/editorial_move_refs/{index}",
                f"move `{move_id}` requires exactly one primary section placement; "
                f"found {len(placements)}",
            )
        )

    for section in selected:
        editorial_refs = section.document.get("editorial_move_refs", [])
        if not isinstance(editorial_refs, list):
            editorial_refs = []

        approval_state = _editorial_plan_approval_state(section)
        if approval_state != "approved":
            findings.append(
                _manuscript_finding(
                    "compile.plan_approval",
                    section,
                    "/approvals",
                    "section plan requires a current approved editorial_choice decision",
                )
            )

        dependency_targets = {
            dependency.get("target_id")
            for dependency in section.document.get("dependencies", [])
            if isinstance(dependency, dict)
            and isinstance(dependency.get("target_id"), str)
        }
        research_refs = section.document.get("research_refs", [])
        required_section_targets = [
            *editorial_refs,
            *(research_refs if isinstance(research_refs, list) else []),
        ]
        for target_id in required_section_targets:
            if isinstance(target_id, str) and target_id not in dependency_targets:
                findings.append(
                    _manuscript_finding(
                        "compile.dependency_coverage",
                        section,
                        "/dependencies",
                        f"section dependency snapshot does not cover `{target_id}`",
                    )
                )

        ordered_ids = section.document.get("ordered_block_ids", [])
        if not isinstance(ordered_ids, list):
            continue
        for block_id in ordered_ids:
            block = blocks.get(block_id) if isinstance(block_id, str) else None
            if block is None:
                continue
            block_dependency_targets = {
                dependency.get("target_id")
                for dependency in block.document.get("dependencies", [])
                if isinstance(dependency, dict)
                and isinstance(dependency.get("target_id"), str)
            }
            for field in ("claim_refs", "result_refs", "source_refs", "figure_refs"):
                references = block.document.get(field, [])
                if not isinstance(references, list):
                    continue
                for target_id in references:
                    if (
                        isinstance(target_id, str)
                        and target_id not in block_dependency_targets
                    ):
                        findings.append(
                            _manuscript_finding(
                                "compile.dependency_coverage",
                                block,
                                "/dependencies",
                                f"block dependency snapshot does not cover `{target_id}`",
                            )
                        )
    return findings


def _publication_finding(code: str, pointer: str, message: str) -> ModelFinding:
    return ModelFinding(code, pointer, message)


def validate_publication_semantics(
    document: dict[str, Any],
    catalog: ObjectCatalog,
) -> list[ModelFinding]:
    """Validate candidate approval, round snapshots, and publishable dependencies."""
    findings: list[ModelFinding] = []
    extensions = document.get("extensions")
    if isinstance(extensions, dict):
        for finding in validate_extension_keys(extensions):
            findings.append(
                _publication_finding(
                    finding.code,
                    f"/extensions{finding.pointer}",
                    finding.message,
                )
            )
        for key in extensions:
            if isinstance(key, str) and _sensitive_extension_key(key):
                findings.append(
                    _publication_finding(
                        "semantic.extension",
                        f"/extensions/{key.replace('~', '~0').replace('/', '~1')}",
                        "Publication extension may not store credential or local-path state",
                    )
                )
        for pointer, value in _walk_issue_strings(extensions):
            if _issue_sensitive_text(value):
                findings.append(
                    _publication_finding(
                        "semantic.confidentiality",
                        f"/extensions{pointer}",
                        "Publication extensions may contain only public or opaque references",
                    )
                )

    venue = document.get("venue")
    requirements = venue.get("requirements", []) if isinstance(venue, dict) else []
    requirement_ids: set[str] = set()
    if isinstance(requirements, list):
        for index, requirement in enumerate(requirements):
            requirement_id = requirement.get("id") if isinstance(requirement, dict) else None
            if isinstance(requirement_id, str):
                if requirement_id in requirement_ids:
                    findings.append(
                        _publication_finding(
                            "reference.duplicate",
                            f"/venue/requirements/{index}/id",
                            f"duplicate requirement ID `{requirement_id}`",
                        )
                    )
                requirement_ids.add(requirement_id)

    rounds = document.get("rounds", [])
    round_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    snapshot_paths: dict[str, int] = {}
    if isinstance(rounds, list):
        for index, round_document in enumerate(rounds):
            if not isinstance(round_document, dict):
                continue
            round_id = round_document.get("id")
            if isinstance(round_id, str):
                if round_id in round_by_id:
                    findings.append(
                        _publication_finding(
                            "reference.duplicate",
                            f"/rounds/{index}/id",
                            f"duplicate round ID `{round_id}`",
                        )
                    )
                else:
                    round_by_id[round_id] = (index, round_document)
            snapshot_path = round_document.get("snapshot_path")
            if isinstance(snapshot_path, str):
                path = PurePosixPath(snapshot_path)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "submission":
                    findings.append(
                        _publication_finding(
                            "reference.path",
                            f"/rounds/{index}/snapshot_path",
                            "snapshot path must stay under the relative submission/ tree",
                        )
                    )
                if snapshot_path in snapshot_paths:
                    findings.append(
                        _publication_finding(
                            "semantic.snapshot_path",
                            f"/rounds/{index}/snapshot_path",
                            f"snapshot path duplicates round {snapshot_paths[snapshot_path]}",
                        )
                    )
                else:
                    snapshot_paths[snapshot_path] = index
            if round_document.get("status") in {
                "submitted", "under_review", "resubmitted", "accepted", "rejected", "withdrawn",
            } and round_document.get("immutable") is not True:
                findings.append(
                    _publication_finding(
                        "immutability.required",
                        f"/rounds/{index}/immutable",
                        "submitted-or-later rounds must be marked immutable",
                    )
                )

    current_round_id = document.get("current_round_id")
    current_round_entry = round_by_id.get(current_round_id) if isinstance(current_round_id, str) else None
    if current_round_id and current_round_entry is None:
        findings.append(
            _publication_finding(
                "reference.dangling",
                "/current_round_id",
                f"current round `{current_round_id}` does not exist",
            )
        )
    if current_round_entry is not None:
        round_index, current_round = current_round_entry
        if document.get("submission_state") != current_round.get("status"):
            findings.append(
                _publication_finding(
                    "semantic.round_state",
                    "/submission_state",
                    "submission state must match the current round status",
                )
            )

    approvals = document.get("submission_approvals", [])
    if isinstance(rounds, list):
        for round_index, round_document in enumerate(rounds):
            if not isinstance(round_document, dict):
                continue
            history = [
                approval
                for approval in approvals
                if isinstance(approval, dict)
                and approval.get("kind") == "submission"
                and approval.get("candidate_id") == round_document.get("candidate_id")
            ] if isinstance(approvals, list) else []
            bound = [
                approval
                for approval in history
                if approval.get("candidate_revision") == round_document.get("candidate_revision")
                and approval.get("candidate_hash") == round_document.get("candidate_hash")
            ]
            if history and not bound:
                findings.append(
                    _publication_finding(
                        "approval.stale",
                        f"/rounds/{round_index}/candidate_hash",
                        "round candidate hash is not bound by its submission approval history",
                    )
                )
            elif not bound or bound[-1].get("decision") != "approved":
                findings.append(
                    _publication_finding(
                        "approval.missing",
                        f"/rounds/{round_index}/candidate_hash",
                        "round requires an approved historical submission decision",
                    )
                )

    current_candidate = document.get("current_candidate")
    if not isinstance(current_candidate, dict):
        return findings

    candidate_id = current_candidate.get("id")
    candidate_revision = current_candidate.get("revision")
    candidate_hash = semantic_hash(current_candidate)
    candidate_status = current_candidate.get("status")
    if not current_round_id and document.get("submission_state") != candidate_status:
        findings.append(
            _publication_finding(
                "semantic.candidate_state",
                "/submission_state",
                "without a frozen round, submission state must match candidate status",
            )
        )

    if candidate_status == "gated":
        history = [
            approval
            for approval in approvals
            if isinstance(approval, dict)
            and approval.get("kind") == "submission"
            and approval.get("candidate_id") == candidate_id
        ] if isinstance(approvals, list) else []
        current = [
            approval
            for approval in history
            if approval.get("candidate_revision") == candidate_revision
            and approval.get("candidate_hash") == candidate_hash
        ]
        if history and not current:
            findings.append(
                _publication_finding(
                    "approval.stale",
                    "/submission_approvals",
                    "submission approval does not match the current candidate revision/hash",
                )
            )
        elif not current or current[-1].get("decision") != "approved":
            findings.append(
                _publication_finding(
                    "approval.missing",
                    "/submission_approvals",
                    "gated or frozen candidate requires current human submission approval",
                )
            )

    if candidate_status == "gated" and isinstance(requirements, list):
        pending = [
            requirement
            for requirement in requirements
            if isinstance(requirement, dict)
            and requirement.get("status") == "pending"
        ]
        if pending:
            findings.append(
                _publication_finding(
                    "semantic.venue_requirement",
                    "/venue/requirements",
                    "gated candidate cannot retain pending venue requirements",
                )
            )

    if current_round_entry is not None:
        round_index, current_round = current_round_entry
        same_candidate_revision = (
            current_round.get("candidate_id") == candidate_id
            and current_round.get("candidate_revision") == candidate_revision
        )
        snapshot_matches_candidate = (
            current_round.get("candidate_hash") == candidate_hash
            and current_round.get("source_commit") == current_candidate.get("source_commit")
            and current_round.get("gate_report_ref") == current_candidate.get("gate_report_ref")
            and current_round.get("artifact_refs") == current_candidate.get("artifact_refs")
            and current_round.get("snapshot_dependencies") == current_candidate.get("snapshot_dependencies")
        )
        if same_candidate_revision and not snapshot_matches_candidate:
            findings.append(
                _publication_finding(
                    "immutability.required",
                    f"/rounds/{round_index}/candidate_hash",
                    "a submitted candidate revision cannot be rewritten in place",
                )
            )

    reference_contracts = (
        ("claim_refs", "claim"),
        ("manuscript_section_refs", "section"),
        ("manuscript_block_refs", "block"),
        ("analysis_request_refs", "analysis_request"),
        ("required_response_refs", "response"),
    )
    for field, expected_type in reference_contracts:
        values = current_candidate.get(field, [])
        if not isinstance(values, list):
            continue
        for index, object_id in enumerate(values):
            target = catalog.objects.get(object_id) if isinstance(object_id, str) else None
            pointer = f"/current_candidate/{field}/{index}"
            if target is None or target.object_type != expected_type:
                code = "semantic.response_missing" if expected_type == "response" else "reference.dangling"
                findings.append(
                    _publication_finding(
                        code,
                        pointer,
                        f"required {expected_type} `{object_id}` is not present",
                    )
                )
                continue
            if expected_type == "claim":
                approval_state = _scientific_approval_state(target)
                if approval_state != "approved":
                    findings.append(
                        _publication_finding(
                            "approval.stale" if approval_state == "stale" else "approval.missing",
                            pointer,
                            f"claim `{object_id}` lacks current scientific approval",
                        )
                    )
                if (
                    target.document.get("status") != "approved"
                    or target.document.get("gate_status") != "ready_to_write"
                ):
                    findings.append(
                        _publication_finding(
                            "semantic.claim_not_writable",
                            pointer,
                            f"claim `{object_id}` is not approved and ready_to_write",
                        )
                    )
            elif expected_type == "block":
                if (
                    target.document.get("status") == "stale"
                    or target.document.get("dependency_hash")
                    != target.document.get("last_verified_dependency_hash")
                ):
                    findings.append(
                        _publication_finding(
                            "dependency.stale",
                            pointer,
                            f"manuscript block `{object_id}` is stale",
                        )
                    )
            elif expected_type == "analysis_request":
                if target.document.get("status") != "reconciled":
                    findings.append(
                        _publication_finding(
                            "semantic.predicted_unresolved",
                            pointer,
                            f"analysis request `{object_id}` is not reconciled",
                        )
                    )
            elif expected_type == "response" and target.document.get("status") != "closed":
                findings.append(
                    _publication_finding(
                        "semantic.response_missing",
                        pointer,
                        f"required response `{object_id}` is not closed",
                    )
                )

    snapshot_dependencies = current_candidate.get("snapshot_dependencies", [])
    if isinstance(snapshot_dependencies, list):
        for index, dependency in enumerate(snapshot_dependencies):
            target_id = dependency.get("target_id") if isinstance(dependency, dict) else None
            target = catalog.objects.get(target_id) if isinstance(target_id, str) else None
            if target is None:
                continue
            pointer = f"/current_candidate/snapshot_dependencies/{index}/target_id"
            if target.object_type == "analysis_request" and target.document.get("status") != "reconciled":
                findings.append(
                    _publication_finding(
                        "semantic.predicted_unresolved",
                        pointer,
                        f"snapshot analysis request `{target_id}` is not reconciled",
                    )
                )
            elif target.object_type == "claim":
                approval_state = _scientific_approval_state(target)
                if approval_state != "approved":
                    findings.append(
                        _publication_finding(
                            "approval.stale" if approval_state == "stale" else "approval.missing",
                            pointer,
                            f"snapshot claim `{target_id}` lacks current scientific approval",
                        )
                    )
                if (
                    target.document.get("status") != "approved"
                    or target.document.get("gate_status") != "ready_to_write"
                ):
                    findings.append(
                        _publication_finding(
                            "semantic.claim_not_writable",
                            pointer,
                            f"snapshot claim `{target_id}` is not approved and ready_to_write",
                        )
                    )
            elif target.object_type == "block" and (
                target.document.get("status") == "stale"
                or target.document.get("dependency_hash")
                != target.document.get("last_verified_dependency_hash")
            ):
                findings.append(
                    _publication_finding(
                        "dependency.stale",
                        pointer,
                        f"snapshot manuscript block `{target_id}` is stale",
                    )
                )
            elif target.object_type == "response" and target.document.get("status") != "closed":
                findings.append(
                    _publication_finding(
                        "semantic.response_missing",
                        pointer,
                        f"snapshot response `{target_id}` is not closed",
                    )
                )

    review_round_ref = current_candidate.get("review_round_ref")
    if review_round_ref:
        review_round = catalog.objects.get(review_round_ref)
        if review_round is None or review_round.object_type != "review_round":
            findings.append(
                _publication_finding(
                    "reference.dangling",
                    "/current_candidate/review_round_ref",
                    f"review round `{review_round_ref}` is not present",
                )
            )

    return findings


def _validate_public_provenance(
    obj: CatalogObject,
    values: Any,
    suffix: str,
    findings: list[ModelFinding],
) -> None:
    if not isinstance(values, list):
        return
    for index, value in enumerate(values):
        if not isinstance(value, str) or not _valid_public_provenance(value):
            findings.append(
                _research_finding(
                    "semantic.public_provenance",
                    obj,
                    f"{suffix}/{index}",
                    "provenance must use a public or opaque identifier, not a local/raw path",
                )
            )


def _sensitive_extension_key(key: str) -> bool:
    components = [
        component
        for component in re.split(r"[-._]", key.casefold())
        if component
    ]
    if any(
        component in {"password", "passwd", "secret", "credential", "apikey"}
        for component in components
    ):
        return True
    sensitive_pairs = {
        ("api", "key"),
        ("access", "token"),
        ("auth", "token"),
        ("local", "path"),
        ("private", "key"),
        ("bearer", "token"),
        ("refresh", "token"),
        ("session", "token"),
        ("id", "token"),
    }
    return any(pair in sensitive_pairs for pair in zip(components, components[1:]))


def _valid_public_provenance(value: str) -> bool:
    if any(ord(character) < 32 or character.isspace() for character in value):
        return False
    if value.startswith("artifact:"):
        return re.fullmatch(r"artifact:[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None
    if value.startswith("commit:"):
        return re.fullmatch(r"commit:[0-9a-fA-F]{7,64}", value) is not None
    if value.startswith("doi:"):
        return (
            re.fullmatch(
                r"doi:10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+",
                value,
            )
            is not None
        )
    if value.startswith("url:"):
        if "\\" in value:
            return False
        try:
            parsed = urlsplit(value[4:])
        except ValueError:
            return False
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or bool(parsed.fragment)
        ):
            return False
        hostname = parsed.hostname.casefold().rstrip(".")
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            ipv4_like_labels = hostname.split(".")
            if (
                (
                    1 < len(ipv4_like_labels) <= 4
                    and all(
                        re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)", label)
                        is not None
                        for label in ipv4_like_labels
                    )
                )
                or "." not in hostname
                or hostname == "localhost"
                or hostname.endswith(
                    (
                        ".localhost", ".local", ".internal", ".lan",
                        ".localdomain", ".home.arpa",
                    )
                )
                or hostname in {"localdomain", "home.arpa"}
            ):
                return False
        else:
            if not address.is_global:
                return False
        sensitive_query_keys = {
            "token", "key", "password", "passwd", "secret", "credential",
            "api_key", "apikey", "access_token", "auth",
        }
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
            normalized = key.casefold().replace("-", "_")
            components = set(re.split(r"[._]", normalized))
            if normalized in sensitive_query_keys or components.intersection(
                {"token", "key", "password", "passwd", "secret", "credential", "auth"}
            ):
                return False
        return True
    return False


def _exception_finding(error: Exception, pointer: str) -> ModelFinding:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    if separator and "." in prefix and " " not in prefix:
        detail = detail.strip()
        if detail.startswith("/") and ":" in detail:
            error_pointer, _, error_detail = detail.partition(":")
            if pointer != "/":
                error_pointer = pointer + (
                    "" if error_pointer == "/" else error_pointer
                )
            return ModelFinding(prefix, error_pointer, error_detail.strip())
        return ModelFinding(prefix, pointer, detail)
    return ModelFinding("document.load", pointer, message)


def _prefix_schema_finding(finding: ModelFinding, base: str) -> ModelFinding:
    suffix = "" if finding.pointer in ("", "/") else finding.pointer
    return ModelFinding(finding.code, base + suffix, finding.message, finding.severity)


def _unsafe_relative_path(value: str) -> bool:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    return (
        not value
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or bool(windows.root)
        or ".." in posix.parts
        or ".." in windows.parts
    )


def _safe_record_path(
    root: Path,
    path_prefix: Path,
    value: Any,
) -> Path | None:
    if not isinstance(value, str) or _unsafe_relative_path(value):
        return None
    root_resolved = root.resolve()
    prefix_resolved = path_prefix.resolve()
    candidate = root / Path(value)
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError):
        return None
    if not resolved.is_relative_to(root_resolved):
        return None
    if not resolved.is_relative_to(prefix_resolved):
        return None
    return candidate


def _load_base(entry: RegistryEntry, path: Path) -> tuple[Any | None, list[ModelFinding]]:
    try:
        document = load_document(path)
        schema = load_document(entry.schema_path)
        validate_document_version(entry, document)
        return document, validate_schema(document, schema)
    except Exception as error:
        return None, [_exception_finding(error, "/")]


def _row_value(row: Any, key: str) -> Any:
    return row.get(key) if isinstance(row, dict) else None


def _orphan_findings(
    entry: RegistryEntry,
    referenced: set[Path],
    *,
    strict: bool,
) -> list[ModelFinding]:
    findings: list[ModelFinding] = []
    severity = "error" if strict else "warning"
    scanned_prefixes: set[Path] = set()
    for record_set in entry.record_sets.values():
        prefix = record_set.path_prefix
        resolved_prefix = prefix.resolve()
        if resolved_prefix in scanned_prefixes or not prefix.is_dir():
            continue
        scanned_prefixes.add(resolved_prefix)
        for candidate in sorted(prefix.rglob("*")):
            if (
                candidate.absolute() in referenced
                or candidate.resolve(strict=False) in referenced
            ):
                continue
            if candidate.is_symlink():
                resolved = candidate.resolve(strict=False)
                if not resolved.is_relative_to(prefix.resolve()):
                    findings.append(
                        ModelFinding(
                            "reference.path",
                            "/records",
                            f"record symlink escapes its registered path prefix: {candidate}",
                        )
                    )
                elif candidate.suffix.lower() in {".json", ".yml", ".yaml"}:
                    findings.append(
                        ModelFinding(
                            "reference.orphan",
                            "/records",
                            f"record file is not listed in the index: {candidate}",
                            severity,
                        )
                    )
                continue
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".json", ".yml", ".yaml"}:
                continue
            findings.append(
                ModelFinding(
                    "reference.orphan",
                    "/records",
                    f"record file is not listed in the index: {candidate}",
                    severity,
                )
            )
    return findings


def _load_index_records(
    root: Path,
    entry: RegistryEntry,
    document: Any,
    *,
    strict: bool,
) -> tuple[list[RecordDocument], list[ModelFinding]]:
    rows = document.get("records", []) if isinstance(document, dict) else []
    if not isinstance(rows, list):
        return [], []
    ids = [_row_value(row, "id") for row in rows]
    duplicate_ids = {
        value for value, count in Counter(value for value in ids if isinstance(value, str)).items() if count > 1
    }
    records: list[RecordDocument] = []
    findings: list[ModelFinding] = []
    referenced: set[Path] = set()
    seen_duplicates: set[str] = set()
    for index, row in enumerate(rows):
        base = f"/records/{index}"
        row_id = _row_value(row, "id")
        if isinstance(row_id, str) and row_id in duplicate_ids:
            if row_id in seen_duplicates:
                findings.append(ModelFinding("reference.duplicate", f"{base}/id", f"duplicate ID `{row_id}`"))
            seen_duplicates.add(row_id)
            continue
        record_type = _row_value(row, "record_type")
        record_set = entry.record_sets.get(record_type) if isinstance(record_type, str) else None
        if record_set is None:
            findings.append(ModelFinding("reference.type", f"{base}/record_type", f"unknown record type `{record_type}`"))
            continue
        raw_path = _row_value(row, "document")
        if isinstance(raw_path, str) and not _unsafe_relative_path(raw_path):
            referenced.add((root / Path(raw_path)).absolute())
        path = _safe_record_path(root, record_set.path_prefix, raw_path)
        if path is None:
            findings.append(ModelFinding("reference.path", f"{base}/document", "record document must stay inside its registered path prefix"))
            continue
        resolved = path.resolve(strict=False)
        referenced.add(resolved)
        if not path.is_file():
            findings.append(ModelFinding("reference.document", f"{base}/document", f"record document is missing: {path}"))
            continue
        try:
            record = load_document(path)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/document"))
            continue
        envelope_findings: list[ModelFinding] = []
        actual_id: Any = None
        actual_type: Any = None
        actual_revision: Any = None
        if isinstance(record, dict):
            actual_id = record.get("id")
            actual_type = record.get("record_type")
            actual_revision = record.get("revision")
            for code, pointer, expected, actual in (
                ("index.id", "id", row_id, actual_id),
                ("index.type", "record_type", record_type, actual_type),
                (
                    "index.revision",
                    "expected_revision",
                    _row_value(row, "expected_revision"),
                    actual_revision,
                ),
            ):
                if expected != actual:
                    envelope_findings.append(
                        ModelFinding(
                            code,
                            f"{base}/{pointer}",
                            f"index value {expected!r} does not match record value {actual!r}",
                        )
                    )
            if (
                not isinstance(actual_id, str)
                or re.fullmatch(record_set.id_pattern, actual_id) is None
            ):
                envelope_findings.append(
                    ModelFinding(
                        "index.id",
                        f"{base}/id",
                        f"record ID `{actual_id}` does not match the registered pattern",
                    )
                )
        findings.extend(envelope_findings)
        try:
            schema = load_document(record_set.schema_path)
            schema_findings = validate_schema(record, schema)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/document"))
            continue
        if schema_findings:
            findings.extend(_prefix_schema_finding(finding, f"{base}/document") for finding in schema_findings)
            continue
        if not isinstance(record, dict):
            continue
        mismatched = bool(envelope_findings)
        try:
            digest = semantic_hash(record, excluded_paths=record_set.hash_excluded_paths)
        except Exception as error:
            findings.append(_exception_finding(error, f"{base}/expected_hash"))
            continue
        if _row_value(row, "expected_hash") != digest:
            findings.append(ModelFinding("index.hash", f"{base}/expected_hash", "index hash does not match the canonical record hash"))
            mismatched = True
        if mismatched or not isinstance(actual_revision, int) or isinstance(actual_revision, bool):
            continue
        records.append(RecordDocument(entry.name, record_type, path, record, actual_id, actual_revision, digest, base))
    findings.extend(_orphan_findings(entry, referenced, strict=strict))
    return records, findings


def load_model_document(
    root: Path,
    entry: RegistryEntry,
    *,
    document_path: Path | None = None,
    strict: bool = False,
) -> ModelDocument:
    """Load one registry model without falling back when an index record is invalid."""
    path = document_path or entry.default_path
    document, schema_findings = _load_base(entry, path)
    if document is None or schema_findings or entry.document_kind != "index":
        return ModelDocument(entry, path, document, tuple(schema_findings))
    actual_model_name = (
        document.get("model_name") if isinstance(document, dict) else None
    )
    if actual_model_name != entry.name:
        return ModelDocument(
            entry,
            path,
            document,
            (),
            catalog_findings=(
                ModelFinding(
                    "index.model_name",
                    "/model_name",
                    f"index model_name {actual_model_name!r} does not match "
                    f"registry model {entry.name!r}",
                ),
            ),
        )
    records, findings = _load_index_records(root.resolve(), entry, document, strict=strict)
    return ModelDocument(entry, path, document, (), tuple(records), tuple(findings))


def build_object_catalog(models: Iterable[ModelDocument]) -> ObjectCatalog:
    """Build a global catalog only from schema-clean record documents."""
    candidates: dict[str, list[CatalogObject]] = {}
    for model in models:
        for record in model.records:
            obj = CatalogObject(record.object_id, record.record_type, record.model_name, record.document, record.revision, record.object_hash, record.pointer)
            candidates.setdefault(record.object_id, []).append(obj)
        if not model.schema_clean or not isinstance(model.document, dict):
            continue
        virtual_specs = {
            "editorial": (
                ("story_candidates", "story"),
                ("argument_moves", "move"),
                ("visual_obligations", "visual"),
            ),
            "results_hierarchy": (("items", "results_item"),),
        }.get(model.entry.name, ())
        for field, object_type in virtual_specs:
            values = model.document.get(field, [])
            if not isinstance(values, list):
                continue
            for index, value in enumerate(values):
                if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                    continue
                object_id = value["id"]
                pointer = f"/{field}/{index}"
                obj = CatalogObject(
                    object_id,
                    object_type,
                    model.entry.name,
                    value,
                    None,
                    semantic_hash(value),
                    pointer,
                )
                candidates.setdefault(object_id, []).append(obj)
    objects: dict[str, CatalogObject] = {}
    findings: list[ModelFinding] = []
    for object_id, occurrences in candidates.items():
        if len(occurrences) > 1:
            findings.append(
                ModelFinding(
                    "reference.duplicate",
                    occurrences[1].pointer + "/id",
                    f"duplicate ID `{object_id}`",
                )
            )
        else:
            objects[object_id] = occurrences[0]
    return ObjectCatalog(objects, tuple(findings))
