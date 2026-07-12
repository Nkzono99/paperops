"""Pure projection of validated compiler inputs into Writer-facing DTOs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .contracts import ResolvedContract
from .inputs import LoadedCatalogObject, LoadedCompileInputs
from .privacy import scan_private_material
from .storage import semantic_hash
from .tex import (
    AnalysisRequestSnapshot,
    ManuscriptSnapshot,
    TexBlockBinding,
    bind_typed_tex_blocks,
)
from .types import (
    AuthoritySnapshot,
    CompileBundle,
    CompileFinding,
    CompileRequest,
    InputSnapshot,
    SectionPlan,
    WriteScope,
    WriterPacket,
    _freeze_json,
    _json_compatible,
    _typed_tuple,
    _validate_hash,
    _validate_id,
)


_COMPILER_CONTRACT_VERSION = "p3-typed-compile-v1"
_RESEARCH_TYPES = frozenset(
    {"claim", "result", "source", "figure", "scientific_gate"}
)
_CONTRACT_REQUIRED_FUNCTIONS = {
    "methods": ("logic_chain", "information_placement"),
    "results": ("subsection_contract", "paragraph_contract"),
    "discussion": ("logic_chain", "claim_types"),
}
_PREDICTION_MARKERS = frozenset(
    {"PREDICTED-RESULT", "SIM-REQUEST", "EXPECTATION-BASIS", "REPLACE-XX"}
)
_OPEN_ANALYSIS_REQUEST_STATUSES = frozenset(
    {"planned", "predicted", "analysis-needed", "open", "running"}
)
_RELATION_BY_TYPE = {
    "section": "target-section",
    "block": "target-block",
    "story": "story-context",
    "move": "argument-move",
    "visual": "visual-obligation",
    "results_item": "results-hierarchy",
    "claim": "approved-claim",
    "result": "evidence-result",
    "source": "evidence-source",
    "figure": "evidence-figure",
    "scientific_gate": "scientific-gate",
}


@dataclass(frozen=True)
class CompileContractSnapshot:
    """Canonical aggregate of the resolved contracts used by one compile."""

    contracts: Mapping[str, ResolvedContract]
    snapshot_hash: str = ""

    def __post_init__(self) -> None:
        ordered: dict[str, ResolvedContract] = {}
        for section_kind, contract in sorted(self.contracts.items()):
            if not isinstance(section_kind, str) or not isinstance(
                contract, ResolvedContract
            ):
                raise TypeError("contracts must map section kinds to ResolvedContract")
            if section_kind != contract.section_kind:
                raise ValueError("contract key must equal its resolved section kind")
            ordered[section_kind] = contract
        aggregate = semantic_hash(
            {
                "schema_version": 1,
                "contracts": {
                    kind: contract.to_dict() for kind, contract in ordered.items()
                },
            }
        )
        if self.snapshot_hash and self.snapshot_hash != aggregate:
            raise ValueError("contract snapshot hash does not match its contracts")
        object.__setattr__(self, "contracts", MappingProxyType(ordered))
        object.__setattr__(self, "snapshot_hash", aggregate)

    @classmethod
    def from_contracts(
        cls,
        contracts: Iterable[ResolvedContract],
    ) -> "CompileContractSnapshot":
        by_kind: dict[str, ResolvedContract] = {}
        for contract in contracts:
            if not isinstance(contract, ResolvedContract):
                raise TypeError("contracts must contain only ResolvedContract values")
            if contract.section_kind in by_kind:
                raise ValueError("contract section kind is duplicated")
            by_kind[contract.section_kind] = contract
        return cls(by_kind)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "contracts": {
                kind: contract.to_dict()
                for kind, contract in self.contracts.items()
            },
            "snapshot_hash": self.snapshot_hash,
        }


def _finding(
    code: str,
    pointer: str,
    message: str,
    *,
    severity: str = "error",
    identity: str = "",
) -> CompileFinding:
    return CompileFinding(
        code=code,
        pointer=pointer,
        message=message,
        severity=severity,
        identity=identity,
    )


def _stable_findings(findings: Iterable[CompileFinding]) -> tuple[CompileFinding, ...]:
    by_key: dict[tuple[str, str, str, str, str], CompileFinding] = {}
    for finding in findings:
        key = (
            finding.code,
            finding.pointer,
            finding.severity,
            finding.identity,
            finding.message,
        )
        by_key.setdefault(key, finding)
    return tuple(by_key[key] for key in sorted(by_key))


def _catalog_by_id(
    objects: Sequence[LoadedCatalogObject],
) -> tuple[dict[str, LoadedCatalogObject], list[CompileFinding]]:
    catalog: dict[str, LoadedCatalogObject] = {}
    findings: list[CompileFinding] = []
    for item in objects:
        previous = catalog.get(item.object_id)
        if previous is not None:
            findings.append(
                _finding(
                    "compile.dependency_duplicate",
                    "/objects",
                    "compile catalog contains a duplicate object identity",
                )
            )
            continue
        catalog[item.object_id] = item
    return catalog, findings


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _reference_edges(
    item: LoadedCatalogObject,
) -> tuple[tuple[str, str, frozenset[str]], ...]:
    document = item.document
    edges: list[tuple[str, str, frozenset[str]]] = []

    def add(field: str, expected: str | frozenset[str]) -> None:
        expected_types = (
            frozenset({expected}) if isinstance(expected, str) else expected
        )
        for index, object_id in enumerate(_strings(document.get(field))):
            edges.append((f"/{field}/{index}", object_id, expected_types))

    if item.object_type == "story":
        add("argument_move_ids", "move")
        add("result_order", "results_item")
    elif item.object_type == "move":
        add("claim_ids", "claim")
        add("result_item_ids", "results_item")
        next_id = document.get("next_move_id")
        if isinstance(next_id, str) and next_id:
            edges.append(("/next_move_id", next_id, frozenset({"move"})))
    elif item.object_type == "visual":
        add("claim_ids", "claim")
        add("figure_ids", "figure")
    elif item.object_type == "results_item":
        next_id = document.get("next_item_id")
        if isinstance(next_id, str) and next_id:
            edges.append(
                ("/next_item_id", next_id, frozenset({"results_item"}))
            )
    elif item.object_type == "section":
        add("ordered_block_ids", "block")
        add("editorial_move_refs", "move")
        add("research_refs", _RESEARCH_TYPES)
    elif item.object_type == "block":
        add("claim_refs", "claim")
        add("result_refs", "result")
        add("source_refs", "source")
        add("figure_refs", "figure")
    elif item.object_type == "claim":
        gate_id = document.get("gate_id")
        if isinstance(gate_id, str) and gate_id:
            edges.append(
                ("/gate_id", gate_id, frozenset({"scientific_gate"}))
            )
        add("result_refs", "result")
        add("source_refs", "source")
        add("figure_refs", "figure")
    elif item.object_type == "result":
        add("claim_refs", "claim")
        add("source_refs", "source")
        add("figure_refs", "figure")
    elif item.object_type == "figure":
        add("claim_refs", "claim")
        add("result_refs", "result")
    elif item.object_type == "source":
        add("claim_refs", "claim")
    elif item.object_type == "scientific_gate":
        claim_id = document.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            edges.append(("/claim_id", claim_id, frozenset({"claim"})))
    return tuple(edges)


def _editorial_document(inputs: LoadedCompileInputs) -> Mapping[str, object] | None:
    for document in inputs.documents:
        if document.model_name == "editorial" and document.document_type == "aggregate":
            return document.document
    return None


def _manuscript_topology(
    inputs: LoadedCompileInputs,
    catalog: Mapping[str, LoadedCatalogObject],
) -> tuple[
    tuple[LoadedCatalogObject, ...],
    tuple[LoadedCatalogObject, ...],
    list[CompileFinding],
]:
    """Return current section/block order from the validated Manuscript index."""
    index = next(
        (
            item
            for item in inputs.documents
            if item.model_name == "manuscript" and item.document_type == "index"
        ),
        None,
    )
    findings: list[CompileFinding] = []
    if index is None:
        return (), (), [
            _finding(
                "compile.manuscript_index",
                "/manuscript",
                "validated Manuscript index is missing",
            )
        ]
    records = index.document.get("records", ())
    if not isinstance(records, (list, tuple)):
        return (), (), [
            _finding(
                "compile.manuscript_index",
                "/manuscript/records",
                "validated Manuscript index records are invalid",
                identity=index.identity,
            )
        ]
    section_ids = tuple(
        str(row["id"])
        for row in records
        if isinstance(row, Mapping)
        and row.get("record_type") == "section"
        and isinstance(row.get("id"), str)
    )
    if len(section_ids) != len(set(section_ids)):
        findings.append(
            _finding(
                "compile.manuscript_index",
                "/manuscript/records",
                "Manuscript index contains duplicate section identities",
                identity=index.identity,
            )
        )
    catalog_section_ids = {
        item.object_id for item in catalog.values() if item.object_type == "section"
    }
    if set(section_ids) != catalog_section_ids:
        findings.append(
            _finding(
                "compile.manuscript_index",
                "/manuscript/records",
                "Manuscript index does not exactly cover current sections",
                identity=index.identity,
            )
        )
    sections = tuple(
        item
        for section_id in section_ids
        if (item := catalog.get(section_id)) is not None
        and item.object_type == "section"
    )
    block_ids = tuple(
        block_id
        for section in sections
        for block_id in _strings(section.document.get("ordered_block_ids"))
    )
    if len(block_ids) != len(set(block_ids)):
        findings.append(
            _finding(
                "compile.manuscript_index",
                "/manuscript/records",
                "Manuscript topology reuses a block identity",
                identity=index.identity,
            )
        )
    blocks = tuple(
        item
        for block_id in block_ids
        if (item := catalog.get(block_id)) is not None and item.object_type == "block"
    )
    catalog_block_ids = {
        item.object_id for item in catalog.values() if item.object_type == "block"
    }
    if len(blocks) != len(block_ids) or set(block_ids) != catalog_block_ids:
        findings.append(
            _finding(
                "compile.manuscript_index",
                "/manuscript/records",
                "Manuscript topology references a missing or wrong-type block",
                identity=index.identity,
            )
        )
    return sections, blocks, findings


def _seed_ids(
    editorial: Mapping[str, object] | None,
    target_ids: tuple[str, ...],
) -> tuple[str, ...]:
    seeds = list(target_ids)
    if editorial is None:
        return tuple(seeds)
    selected = editorial.get("selected_story_id")
    if isinstance(selected, str) and selected:
        seeds.append(selected)
    stories = editorial.get("story_candidates")
    if isinstance(stories, (list, tuple)):
        for story in stories:
            if isinstance(story, Mapping) and isinstance(story.get("id"), str):
                seeds.append(str(story["id"]))
    claim_roles = editorial.get("claim_roles")
    if isinstance(claim_roles, Mapping):
        for role in ("foreground", "supporting", "supplement", "cut"):
            row = claim_roles.get(role)
            if isinstance(row, Mapping):
                seeds.extend(_strings(row.get("claim_ids")))
    visuals = editorial.get("visual_obligations")
    if isinstance(visuals, (list, tuple)):
        for visual in visuals:
            if isinstance(visual, Mapping) and isinstance(visual.get("id"), str):
                seeds.append(str(visual["id"]))
    return tuple(dict.fromkeys(seeds))


def _authoring_seed_ids(
    editorial: Mapping[str, object] | None,
    target_ids: tuple[str, ...],
) -> tuple[str, ...]:
    seeds = list(target_ids)
    if editorial is None:
        return tuple(seeds)
    selected = editorial.get("selected_story_id")
    if isinstance(selected, str) and selected:
        seeds.append(selected)
    claim_roles = editorial.get("claim_roles")
    if isinstance(claim_roles, Mapping):
        for role in ("foreground", "supporting", "supplement"):
            row = claim_roles.get(role)
            if isinstance(row, Mapping):
                seeds.extend(_strings(row.get("claim_ids")))
    return tuple(dict.fromkeys(seeds))


def _validate_typed_seeds(
    catalog: Mapping[str, LoadedCatalogObject],
    editorial: Mapping[str, object] | None,
    target_ids: tuple[str, ...],
) -> list[CompileFinding]:
    seeds: list[tuple[str, frozenset[str], str]] = [
        (target_id, frozenset({"section"}), "/request/targets")
        for target_id in target_ids
    ]
    if editorial is not None:
        selected = editorial.get("selected_story_id")
        if isinstance(selected, str) and selected:
            seeds.append(
                (selected, frozenset({"story"}), "/editorial/selected_story_id")
            )
        stories = editorial.get("story_candidates")
        if isinstance(stories, (list, tuple)):
            for index, story in enumerate(stories):
                if isinstance(story, Mapping) and isinstance(story.get("id"), str):
                    seeds.append(
                        (
                            str(story["id"]),
                            frozenset({"story"}),
                            f"/editorial/story_candidates/{index}/id",
                        )
                    )
        roles = editorial.get("claim_roles")
        if isinstance(roles, Mapping):
            for role in ("foreground", "supporting", "supplement", "cut"):
                row = roles.get(role)
                if not isinstance(row, Mapping):
                    continue
                for index, claim_id in enumerate(_strings(row.get("claim_ids"))):
                    seeds.append(
                        (
                            claim_id,
                            frozenset({"claim"}),
                            f"/editorial/claim_roles/{role}/claim_ids/{index}",
                        )
                    )
        visuals = editorial.get("visual_obligations")
        if isinstance(visuals, (list, tuple)):
            for index, visual in enumerate(visuals):
                if isinstance(visual, Mapping) and isinstance(visual.get("id"), str):
                    seeds.append(
                        (
                            str(visual["id"]),
                            frozenset({"visual"}),
                            f"/editorial/visual_obligations/{index}/id",
                        )
                    )
    findings: list[CompileFinding] = []
    for object_id, expected_types, pointer in seeds:
        target = catalog.get(object_id)
        if target is None:
            findings.append(
                _finding(
                    "compile.dependency_missing",
                    pointer,
                    "typed compile seed is absent",
                )
            )
        elif target.object_type not in expected_types:
            findings.append(
                _finding(
                    "compile.dependency_type",
                    pointer,
                    "typed compile seed has the wrong type",
                )
            )
    return findings


def _dependency_closure(
    catalog: Mapping[str, LoadedCatalogObject],
    seeds: tuple[str, ...],
    *,
    allowed_move_ids: frozenset[str] | None = None,
) -> tuple[tuple[LoadedCatalogObject, ...], list[CompileFinding]]:
    queue = deque(seeds)
    visited: set[str] = set()
    ordered: list[LoadedCatalogObject] = []
    findings: list[CompileFinding] = []
    while queue:
        object_id = queue.popleft()
        if object_id in visited:
            continue
        visited.add(object_id)
        item = catalog.get(object_id)
        if item is None:
            findings.append(
                _finding(
                    "compile.dependency_missing",
                    "/references",
                    "referenced compile object is absent",
                )
            )
            continue
        ordered.append(item)
        raw_dependencies = item.document.get("dependencies", ())
        if isinstance(raw_dependencies, (list, tuple)):
            for dependency in raw_dependencies:
                if not isinstance(dependency, Mapping):
                    continue
                target_id = dependency.get("target_id")
                if isinstance(target_id, str) and target_id:
                    queue.append(target_id)
        for pointer, target_id, expected_types in _reference_edges(item):
            if (
                item.object_type == "move"
                and pointer == "/next_move_id"
                and allowed_move_ids is not None
                and target_id not in allowed_move_ids
            ):
                continue
            target = catalog.get(target_id)
            if target is None:
                findings.append(
                    _finding(
                        "compile.dependency_missing",
                        f"/{item.object_id}{pointer}",
                        "referenced compile object is absent",
                        identity=item.identity.split("#", 1)[0],
                    )
                )
                continue
            if target.object_type not in expected_types:
                findings.append(
                    _finding(
                        "compile.dependency_type",
                        f"/{item.object_id}{pointer}",
                        "referenced compile object has the wrong type",
                        identity=item.identity.split("#", 1)[0],
                    )
                )
                continue
            queue.append(target_id)
    ordered.sort(key=lambda item: (item.model_name, item.object_type, item.object_id))
    return tuple(ordered), findings


def _validate_declared_dependencies(
    objects: Iterable[LoadedCatalogObject],
    catalog: Mapping[str, LoadedCatalogObject],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for item in objects:
        raw_dependencies = item.document.get("dependencies", ())
        dependencies = (
            raw_dependencies if isinstance(raw_dependencies, (list, tuple)) else ()
        )
        covered: set[str] = set()
        for index, dependency in enumerate(dependencies):
            if not isinstance(dependency, Mapping):
                continue
            target_id = dependency.get("target_id")
            if not isinstance(target_id, str):
                continue
            covered.add(target_id)
            target = catalog.get(target_id)
            if target is None:
                findings.append(
                    _finding(
                        "compile.dependency_missing",
                        f"/{item.object_id}/dependencies/{index}",
                        "declared dependency target is absent",
                        identity=item.identity.split("#", 1)[0],
                    )
                )
                continue
            if dependency.get("expected_hash") != target.semantic_hash:
                findings.append(
                    _finding(
                        "compile.dependency_stale",
                        f"/{item.object_id}/dependencies/{index}/expected_hash",
                        "declared dependency hash is not current",
                        identity=item.identity.split("#", 1)[0],
                    )
                )
            expected_revision = dependency.get("expected_revision")
            if expected_revision is not None and expected_revision != target.revision:
                findings.append(
                    _finding(
                        "compile.dependency_stale",
                        f"/{item.object_id}/dependencies/{index}/expected_revision",
                        "declared dependency revision is not current",
                        identity=item.identity.split("#", 1)[0],
                    )
                )
        required: set[str] = set()
        if item.object_type == "section":
            required.update(_strings(item.document.get("editorial_move_refs")))
            required.update(_strings(item.document.get("research_refs")))
        elif item.object_type == "block":
            for field in ("claim_refs", "result_refs", "source_refs", "figure_refs"):
                required.update(_strings(item.document.get(field)))
        if required - covered:
            findings.append(
                _finding(
                    "compile.dependency_uncovered",
                    f"/{item.object_id}/dependencies",
                    "section or block references are absent from dependency coverage",
                    identity=item.identity.split("#", 1)[0],
                )
            )
    return findings


def _catalog_snapshot(
    item: LoadedCatalogObject,
    *,
    target_section_ids: frozenset[str],
    write_block_ids: frozenset[str],
) -> InputSnapshot:
    relation = _RELATION_BY_TYPE.get(item.object_type, "catalog-dependency")
    if item.object_type == "section" and item.object_id not in target_section_ids:
        relation = "manuscript-topology"
    elif item.object_type == "block" and item.object_id not in write_block_ids:
        relation = "manuscript-topology"
    return InputSnapshot(
        identity=item.identity,
        input_type=item.object_type,
        semantic_hash=item.semantic_hash,
        content_hash=item.content_hash,
        relation=relation,
        model_name=item.model_name,
        revision=item.revision,
        snapshot_kind="catalog",
    )


def _content_snapshot(
    identity: str,
    input_type: str,
    content_hash: str,
    relation: str,
    *,
    semantic: str = "",
) -> InputSnapshot:
    return InputSnapshot(
        identity=identity,
        input_type=input_type,
        semantic_hash=semantic or content_hash,
        content_hash=content_hash,
        relation=relation,
        snapshot_kind="content",
    )


def _input_type(identity: str, bibliography: frozenset[str]) -> str:
    if identity in bibliography:
        return "bibliography"
    if identity.endswith("map.toml"):
        return "mirror-map"
    if identity.endswith("block-ledger.yml"):
        return "mirror-ledger"
    if identity.endswith("terminology.yml"):
        return "terminology"
    if identity.endswith("concept-terms.md"):
        return "concept-terms"
    if identity.startswith("_paperops/model/issues/analysis/") and identity.endswith(
        (".yml", ".yaml")
    ):
        return "analysis-request"
    if identity.endswith(".tex"):
        return "tex-file"
    if identity.endswith("writing-profile.yml"):
        return "writing-profile"
    return "manuscript-context"


def _compile_inputs(
    loaded: LoadedCompileInputs,
    contracts: CompileContractSnapshot,
    manuscript: ManuscriptSnapshot,
    closure: tuple[LoadedCatalogObject, ...],
    bindings: tuple[TexBlockBinding, ...],
    analysis_requests: tuple[AnalysisRequestSnapshot, ...],
    *,
    target_section_ids: frozenset[str],
    write_block_ids: frozenset[str],
) -> tuple[InputSnapshot, ...]:
    items: list[InputSnapshot] = [
        _catalog_snapshot(
            item,
            target_section_ids=target_section_ids,
            write_block_ids=write_block_ids,
        )
        for item in closure
    ]
    items.append(
        _content_snapshot(
            "_paperops/compiler/compile-snapshot.json",
            "compile-snapshot",
            loaded.snapshot_hash,
            "compile-authority",
        )
    )
    for kind, contract in contracts.contracts.items():
        items.append(
            _content_snapshot(
                f"_paperops/compiler/contracts/{kind}.json",
                "resolved-contract",
                contract.snapshot_hash,
                "section-contract",
            )
        )
        for layer in contract.layers:
            items.append(
                _content_snapshot(
                    layer.identity,
                    "contract-layer",
                    layer.content_hash,
                    "contract-layer",
                    semantic=layer.semantic_hash,
                )
            )
    bibliography = frozenset(item.identity for item in manuscript.bibliography_files)
    for read_file in manuscript.read_files:
        input_type = _input_type(read_file.identity, bibliography)
        if input_type == "analysis-request":
            continue
        items.append(
            _content_snapshot(
                read_file.identity,
                input_type,
                read_file.content_hash,
                (
                    "prediction-authority"
                    if input_type == "analysis-request"
                    else "read-context"
                ),
            )
        )
    for request in analysis_requests:
        items.append(
            _content_snapshot(
                request.identity,
                "analysis-request",
                request.content_hash,
                "prediction-authority",
            )
        )
    for binding in bindings:
        items.append(
            _content_snapshot(
                f"{binding.file_identity}#block/{binding.raw_block_id}",
                "tex-block",
                binding.region_hash,
                "tex-preimage",
                semantic=binding.body_hash,
            )
        )
    unique: dict[
        tuple[str, str, str, str, str, int | None], InputSnapshot
    ] = {}
    for item in items:
        key = (
            item.snapshot_kind,
            item.model_name,
            item.input_type,
            item.identity,
            item.relation,
            item.revision,
        )
        unique.setdefault(key, item)
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.snapshot_kind,
                item.model_name,
                item.input_type,
                item.identity,
                item.relation,
                item.revision or 0,
            ),
        )
    )


def _object_projection(
    item: LoadedCatalogObject,
    fields: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": item.object_id,
        **{
            field: _json_compatible(item.document.get(field))
            for field in fields
        },
    }


def _section_field_projection(
    section_kind: str,
    closure: tuple[LoadedCatalogObject, ...],
    contract: ResolvedContract,
) -> dict[str, object]:
    by_type: dict[str, list[LoadedCatalogObject]] = {}
    for item in closure:
        by_type.setdefault(item.object_type, []).append(item)
    if section_kind == "results":
        return {
            "results_hierarchy": [
                _object_projection(
                    item,
                    (
                        "reader_question",
                        "answer",
                        "quantitative_evidence_and_unit_of_analysis",
                        "figure_table_role",
                        "baseline_comparator_rationale",
                        "consequence",
                        "next_item_id",
                    ),
                )
                for item in by_type.get("results_item", [])
            ],
            "results": [
                _object_projection(
                    item,
                    (
                        "observation",
                        "estimand",
                        "unit_of_analysis",
                        "denominator",
                        "comparison",
                        "quantity_contracts",
                        "scope",
                        "limitation",
                    ),
                )
                for item in by_type.get("result", [])
            ],
            "figures": [
                _object_projection(
                    item,
                    (
                        "figure_ref",
                        "reader_task",
                        "takeaway",
                        "manuscript_role",
                    ),
                )
                for item in by_type.get("figure", [])
            ],
        }
    if section_kind == "discussion":
        return {
            "observation": [
                _object_projection(item, ("observation", "scope"))
                for item in by_type.get("result", [])
            ],
            "inference": [
                _object_projection(item, ("statement", "scope"))
                for item in by_type.get("claim", [])
            ],
            "mechanism": [
                _object_projection(item, ("warrant", "assumptions", "scope"))
                for item in by_type.get("claim", [])
            ],
            "alternative": [
                _object_projection(
                    item,
                    (
                        "central_assumptions",
                        "claim_stress_tests",
                        "external_validation_gates",
                        "not_covered",
                    ),
                )
                for item in by_type.get("scientific_gate", [])
            ]
            + [
                _object_projection(
                    item,
                    ("paper_roles", "related_work_role", "claim_boundary"),
                )
                for item in by_type.get("source", [])
            ],
            "implication": [],
            "prediction": [
                _object_projection(item, ("external_validation_gates",))
                for item in by_type.get("scientific_gate", [])
                if item.document.get("external_validation_gates")
            ],
            "limitation": [
                _object_projection(
                    item,
                    ("scope", "limitation", "not_claiming"),
                )
                for item in by_type.get("claim", [])
            ]
            + [
                _object_projection(item, ("limitation", "scope"))
                for item in by_type.get("result", [])
            ]
            + [
                _object_projection(item, ("not_covered",))
                for item in by_type.get("scientific_gate", [])
            ],
        }
    placement = contract.effective.get("information_placement", {})
    if not isinstance(placement, Mapping):
        placement = {}
    return {
        "estimand": [
            {
                "id": item.object_id,
                "value": item.document.get("estimand"),
                "denominator": item.document.get("denominator"),
                "independence_risk": item.document.get("independence_risk"),
                "provenance": _json_compatible(
                    item.document.get("artifact_provenance_ids", ())
                ),
            }
            for item in by_type.get("result", [])
        ],
        "unit_of_analysis": [
            {"id": item.object_id, "value": item.document.get("unit_of_analysis")}
            for item in by_type.get("result", [])
        ],
        "baseline_or_comparator": [
            {"id": item.object_id, "value": _json_compatible(item.document.get("comparison"))}
            for item in by_type.get("result", [])
        ],
        "decision_criteria": [
            _object_projection(item, ("required_checks", "path_criterion"))
            for item in by_type.get("scientific_gate", [])
        ],
        "verification_or_convergence": [
            _object_projection(item, ("evidence_design", "required_checks"))
            for item in by_type.get("scientific_gate", [])
        ],
        "main_text": _json_compatible(placement.get("main_text", ())),
        "supplement": _json_compatible(placement.get("supplement", ())),
        "citation": {
            "placement": _json_compatible(placement.get("citation", ())),
            "sources": [
                _object_projection(
                    item,
                    ("method_precedent", "parameter_choice", "citation_keys"),
                )
                for item in by_type.get("source", [])
            ],
        },
        "code_or_manifest": _json_compatible(
            placement.get("code_or_manifest", ())
        ),
    }


def _evidence_projection(
    closure: tuple[LoadedCatalogObject, ...],
) -> dict[str, object]:
    field_map = {
        "claim": (
            "statement",
            "warrant",
            "scope",
            "limitation",
            "not_claiming",
            "result_refs",
            "source_refs",
            "figure_refs",
            "gate_id",
        ),
        "result": (
            "observation",
            "estimand",
            "unit_of_analysis",
            "denominator",
            "independence_risk",
            "comparison",
            "quantity_contracts",
            "scope",
            "limitation",
            "claim_refs",
            "source_refs",
            "figure_refs",
        ),
        "source": (
            "citation_keys",
            "method_precedent",
            "parameter_choice",
            "paper_roles",
            "related_work_role",
            "claim_boundary",
            "public_provenance_refs",
        ),
        "figure": (
            "figure_ref",
            "reader_task",
            "takeaway",
            "claim_refs",
            "result_refs",
            "manuscript_role",
        ),
        "scientific_gate": (
            "claim_id",
            "gate_decision",
            "required_checks",
            "central_assumptions",
            "claim_stress_tests",
            "external_validation_gates",
            "path_criterion",
            "evidence_design",
            "not_covered",
        ),
        "results_item": (
            "reader_question",
            "answer",
            "quantitative_evidence_and_unit_of_analysis",
            "figure_table_role",
            "baseline_comparator_rationale",
            "consequence",
            "next_item_id",
        ),
    }
    result: dict[str, object] = {}
    for object_type, key in (
        ("claim", "claims"),
        ("result", "results"),
        ("source", "sources"),
        ("figure", "figures"),
        ("scientific_gate", "gates"),
        ("results_item", "results_hierarchy"),
    ):
        result[key] = [
            _object_projection(item, field_map[object_type])
            for item in closure
            if item.object_type == object_type
        ]
    return result


def _global_context(
    editorial: Mapping[str, object],
    catalog: Mapping[str, LoadedCatalogObject],
    all_sections: tuple[LoadedCatalogObject, ...],
    blocks_by_id: Mapping[str, LoadedCatalogObject],
    bindings: tuple[TexBlockBinding, ...],
    manuscript: ManuscriptSnapshot,
) -> dict[str, object]:
    selected_id = editorial.get("selected_story_id")
    selected = catalog.get(selected_id) if isinstance(selected_id, str) else None
    selected_projection = (
        _object_projection(
            selected,
            (
                "label",
                "thesis",
                "result_order",
                "argument_move_ids",
                "selection_reason",
            ),
        )
        if selected is not None
        else {}
    )
    rejected = sorted(
        (
            item
            for item in catalog.values()
            if item.object_type == "story"
            and item.document.get("status") == "rejected"
        ),
        key=lambda item: item.object_id,
    )
    selected_move_ids = (
        _strings(selected.document.get("argument_move_ids")) if selected else ()
    )
    moves = [
        catalog[move_id]
        for move_id in selected_move_ids
        if move_id in catalog and catalog[move_id].object_type == "move"
    ]
    visuals = sorted(
        (item for item in catalog.values() if item.object_type == "visual"),
        key=lambda item: item.object_id,
    )
    public_terms = [
        rule.to_dict()
        for rule in manuscript.terminology_rules
        if rule.status in {"public", "needs_definition"}
    ]
    prohibitions = [
        rule.to_dict()
        for rule in manuscript.terminology_rules
        if rule.status in {"internal_only", "forbidden"}
    ]
    return {
        "schema_version": 1,
        "reader_transformation": _json_compatible(
            editorial.get("reader_transformation", {})
        ),
        "selected_story": selected_projection,
        "rejected_stories": [
            {
                "id": item.object_id,
                "label": item.document.get("label", ""),
                "result_order": list(_strings(item.document.get("result_order"))),
                "argument_move_ids": list(
                    _strings(item.document.get("argument_move_ids"))
                ),
                "rejection_reason": item.document.get("rejection_reason", ""),
            }
            for item in rejected
        ],
        "thesis": selected.document.get("thesis", "") if selected else "",
        "claim_roles": _json_compatible(editorial.get("claim_roles", {})),
        "evidence_ladder": list(
            _strings(selected.document.get("result_order")) if selected else ()
        ),
        "ordered_moves": [
            {
                **_object_projection(
                    item,
                    (
                        "position",
                        "stance",
                        "reader_question",
                        "assertion",
                        "claim_ids",
                        "result_item_ids",
                        "next_move_id",
                    ),
                ),
                "next_move_id": (
                    item.document.get("next_move_id", "")
                    if item.document.get("next_move_id", "")
                    in selected_move_ids
                    else ""
                ),
            }
            for item in moves
        ],
        "section_block_map": [
            {
                "section_id": item.object_id,
                "section_kind": item.document.get("section_kind", ""),
                "previous_section_id": (
                    all_sections[index - 1].object_id if index > 0 else ""
                ),
                "next_section_id": (
                    all_sections[index + 1].object_id
                    if index + 1 < len(all_sections)
                    else ""
                ),
                "ordered_block_ids": list(
                    _strings(item.document.get("ordered_block_ids"))
                ),
                "editorial_move_refs": list(
                    _strings(item.document.get("editorial_move_refs"))
                ),
                "move_bindings": _json_compatible(
                    item.document.get("move_bindings", ())
                ),
                "blocks": [
                    _block_projection(block, bindings)
                    for block_id in _strings(
                        item.document.get("ordered_block_ids")
                    )
                    if (block := blocks_by_id.get(block_id)) is not None
                ],
            }
            for index, item in enumerate(all_sections)
        ],
        "salience": _json_compatible(editorial.get("claim_roles", {})),
        "visual_obligations": [
            _object_projection(
                item,
                (
                    "reader_task",
                    "takeaway",
                    "claim_ids",
                    "preferred_form",
                    "status",
                    "waiver_reason",
                    "figure_ids",
                ),
            )
            for item in visuals
        ],
        "terminology": {
            "public_rules": public_terms,
            "prohibitions": prohibitions,
            "concept_terms": [
                item.to_dict() for item in manuscript.concept_terms
            ],
        },
        "mirror_policy": {
            "sections": [
                {
                    "section_id": item.object_id,
                    "policy": item.document.get("mirror_policy", ""),
                }
                for item in all_sections
            ],
            "file_pairs": [item.to_dict() for item in manuscript.file_pairs],
            "freshness": [item.to_dict() for item in manuscript.freshness],
        },
        "manuscript_read_files": [
            item.to_dict() for item in manuscript.read_files
        ],
        "citation_registry": [
            item.to_dict()
            for item in sorted(
                manuscript.bibliography_files,
                key=lambda item: item.identity,
            )
        ],
        "extensions": {},
    }


def compute_compile_id(
    *,
    compiler_contract_version: str,
    source_mode: str,
    applicable: bool,
    request: CompileRequest,
    authority: Sequence[AuthoritySnapshot],
    inputs: Sequence[InputSnapshot],
    contract_snapshot_hash: str,
    manuscript_snapshot_hash: str,
    global_context: Mapping[str, object],
    section_projections: Mapping[str, Mapping[str, object]],
) -> str:
    """Compute the reusable compile identity from pure canonical material."""
    material = {
        "schema_version": 1,
        "compiler_contract_version": compiler_contract_version,
        "source_mode": source_mode,
        "applicable": applicable,
        "request": request.to_dict(),
        "authority": [
            item.to_dict()
            for item in sorted(authority, key=lambda item: item.model_name)
        ],
        "inputs": [
            item.to_dict()
            for item in sorted(
                inputs,
                key=lambda item: (
                    item.snapshot_kind,
                    item.model_name,
                    item.input_type,
                    item.identity,
                    item.relation,
                    item.revision or 0,
                ),
            )
        ],
        "contract_snapshot_hash": contract_snapshot_hash,
        "manuscript_snapshot_hash": manuscript_snapshot_hash,
        "global_context_hash": semantic_hash(global_context),
        "section_projection_hashes": [
            {
                "section_id": section_id,
                "hash": semantic_hash(projection),
            }
            for section_id, projection in sorted(section_projections.items())
        ],
    }
    return "compile-v1-" + semantic_hash(material).split(":", 1)[1]


def _packet_id(compile_id: str, section_id: str, scope: object) -> str:
    digest = semantic_hash(
        {
            "schema_version": 1,
            "compile_id": compile_id,
            "section_id": section_id,
            "write_scope": scope,
        }
    ).split(":", 1)[1]
    return "packet-v1-" + digest


@dataclass(frozen=True)
class CompileBundleCandidate:
    """A materialization result that is not yet a successful CompileBundle."""

    compiler_contract_version: str
    compile_id: str
    status: str
    source_mode: str
    applicable: bool
    request: CompileRequest
    authority: tuple[AuthoritySnapshot, ...]
    inputs: tuple[InputSnapshot, ...]
    global_context: Mapping[str, Any]
    section_plans: tuple[SectionPlan, ...]
    writer_packets: tuple[WriterPacket, ...]
    findings: tuple[CompileFinding, ...]
    contract_snapshot_hash: str = ""
    manuscript_snapshot_hash: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        _validate_id(self.compiler_contract_version, "compiler contract version")
        _validate_id(self.compile_id, "compile ID")
        if self.status not in {"ready", "blocked"}:
            raise ValueError("compile candidate status must be ready or blocked")
        if self.source_mode not in {"authoritative", "shadow"}:
            raise ValueError("compile candidate source mode is unsupported")
        if type(self.applicable) is not bool:
            raise TypeError("compile candidate applicable must be boolean")
        if (self.source_mode == "authoritative") != self.applicable:
            raise ValueError(
                "authoritative candidates are applicable and shadow candidates are not"
            )
        if not isinstance(self.request, CompileRequest):
            raise TypeError("compile candidate request must be a CompileRequest")
        authority = _typed_tuple(
            self.authority,
            AuthoritySnapshot,
            "compile candidate authority",
        )
        inputs = _typed_tuple(
            self.inputs,
            InputSnapshot,
            "compile candidate inputs",
        )
        plans = _typed_tuple(
            self.section_plans,
            SectionPlan,
            "compile candidate section plans",
        )
        packets = _typed_tuple(
            self.writer_packets,
            WriterPacket,
            "compile candidate Writer packets",
        )
        findings = _typed_tuple(
            self.findings,
            CompileFinding,
            "compile candidate findings",
        )
        has_error = any(finding.severity == "error" for finding in findings)
        if has_error and (plans or packets):
            raise ValueError("blocked compile candidate cannot contain plans or packets")
        if has_error and self.status != "blocked":
            raise ValueError("error findings require a blocked compile candidate")
        if not has_error and self.status != "ready":
            raise ValueError("error-free compile candidate must be ready")
        if self.contract_snapshot_hash:
            _validate_hash(self.contract_snapshot_hash, "contract snapshot hash")
        if self.manuscript_snapshot_hash:
            _validate_hash(self.manuscript_snapshot_hash, "manuscript snapshot hash")
        if self.schema_version != 1:
            raise ValueError("unsupported compile candidate schema version")
        object.__setattr__(self, "authority", authority)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "global_context", _freeze_json(self.global_context))
        object.__setattr__(self, "section_plans", plans)
        object.__setattr__(self, "writer_packets", packets)
        object.__setattr__(self, "findings", findings)

    @property
    def successful(self) -> bool:
        if self.status != "ready" or any(
            finding.severity == "error" for finding in self.findings
        ):
            return False
        if (
            not self.section_plans
            or not self.writer_packets
            or not self.contract_snapshot_hash
            or not self.manuscript_snapshot_hash
            or not self.global_context
        ):
            return False
        compile_snapshots = tuple(
            item for item in self.inputs if item.input_type == "compile-snapshot"
        )
        if len(compile_snapshots) != 1 or any(
            item.snapshot_kind == "catalog" and not item.content_hash
            for item in self.inputs
        ):
            return False
        if self.request.targets and {
            plan.section_id for plan in self.section_plans
        } != set(self.request.targets):
            return False
        for packet in self.writer_packets:
            if (
                tuple(
                    item
                    for item in packet.inputs
                    if item.input_type == "compile-snapshot"
                )
                != compile_snapshots
                or not packet.dependency_profile
                or not packet.dependency_hash
            ):
                return False
        if any(plan.inputs != self.inputs for plan in self.section_plans):
            return False
        return True

    def to_bundle(self) -> CompileBundle:
        if not self.successful:
            raise ValueError("blocked compile candidate cannot become a bundle")
        return CompileBundle(
            compile_id=self.compile_id,
            source_mode=self.source_mode,
            request=self.request,
            authority=self.authority,
            inputs=self.inputs,
            section_plans=self.section_plans,
            writer_packets=self.writer_packets,
            findings=self.findings,
            status=self.status,
            schema_version=self.schema_version,
            compiler_contract_version=self.compiler_contract_version,
            applicable=self.applicable,
            contract_snapshot_hash=self.contract_snapshot_hash,
            manuscript_snapshot_hash=self.manuscript_snapshot_hash,
            global_context=self.global_context,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "compiler_contract_version": self.compiler_contract_version,
            "compile_id": self.compile_id,
            "status": self.status,
            "source_mode": self.source_mode,
            "applicable": self.applicable,
            "contract_snapshot_hash": self.contract_snapshot_hash,
            "manuscript_snapshot_hash": self.manuscript_snapshot_hash,
            "request": self.request.to_dict(),
            "authority": [item.to_dict() for item in self.authority],
            "inputs": [item.to_dict() for item in self.inputs],
            "global_context": _json_compatible(self.global_context),
            "section_plans": [item.to_dict() for item in self.section_plans],
            "writer_packets": [item.to_dict() for item in self.writer_packets],
            "findings": [item.to_dict() for item in self.findings],
        }


def _readiness_findings(inputs: LoadedCompileInputs) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for item in inputs.readiness.findings:
        findings.append(
            _finding(
                str(item.code),
                str(item.pointer),
                str(item.message),
                severity=str(getattr(item, "severity", "error")),
            )
        )
    return findings


def _validate_contracts(
    contracts: CompileContractSnapshot,
    targets: tuple[LoadedCatalogObject, ...],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    target_kinds = {
        str(item.document.get("section_kind")) for item in targets
    }
    if set(contracts.contracts) != target_kinds:
        findings.append(
            _finding(
                "compile.contract_coverage",
                "/contracts",
                "resolved contracts must exactly cover target section kinds",
            )
        )
    for kind, contract in contracts.contracts.items():
        findings.extend(contract.findings)
        for required in _CONTRACT_REQUIRED_FUNCTIONS.get(kind, ()):
            value = contract.effective.get(required)
            if not value:
                findings.append(
                    _finding(
                        "compile.contract_function",
                        f"/contracts/{kind}/{required}",
                        "resolved contract is missing a required section function",
                        identity=contract.layers[0].identity,
                    )
                )
    for section in targets:
        kind = section.document.get("section_kind")
        if _strings(section.document.get("contract_refs")) != (f"contract:{kind}",):
            findings.append(
                _finding(
                    "compile.contract_binding",
                    f"/{section.object_id}/contract_refs",
                    "section contract reference must bind its resolved section kind",
                    identity=section.identity,
                )
            )
    return findings


def _validate_section_invariants(
    targets: tuple[LoadedCatalogObject, ...],
    catalog: Mapping[str, LoadedCatalogObject],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for section in targets:
        if (
            not isinstance(section.revision, int)
            or isinstance(section.revision, bool)
            or section.revision < 1
        ):
            findings.append(
                _finding(
                    "compile.section_revision",
                    f"/{section.object_id}/revision",
                    "section revision must be explicit and positive",
                    identity=section.identity,
                )
            )
        if section.document.get("section_kind") not in _CONTRACT_REQUIRED_FUNCTIONS:
            findings.append(
                _finding(
                    "compile.section_kind",
                    f"/{section.object_id}/section_kind",
                    "section kind is unsupported by the typed compiler",
                    identity=section.identity,
                )
            )
        for index, block_id in enumerate(
            _strings(section.document.get("ordered_block_ids"))
        ):
            block = catalog.get(block_id)
            if (
                block is not None
                and block.object_type == "block"
                and block.document.get("section_id") != section.object_id
            ):
                findings.append(
                    _finding(
                        "compile.scope_topology",
                        f"/{section.object_id}/ordered_block_ids/{index}",
                        "ordered block must name its owning section",
                        identity=section.identity,
                    )
                )
    return findings


def _validate_scope(
    request: CompileRequest,
    targets: tuple[LoadedCatalogObject, ...],
    topology_blocks: tuple[LoadedCatalogObject, ...],
    selected_blocks: tuple[LoadedCatalogObject, ...],
    selected_bindings: tuple[TexBlockBinding, ...],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for field, values in (
        ("languages", request.write_scope.languages),
        ("files", request.write_scope.files),
        ("section_ids", request.write_scope.section_ids),
        ("block_ids", request.write_scope.block_ids),
        ("allowed_operations", request.write_scope.allowed_operations),
    ):
        if len(values) != len(set(values)):
            findings.append(
                _finding(
                    "compile.scope_duplicate",
                    f"/write_scope/{field}",
                    "write scope lists must not contain duplicate values",
                )
            )
    target_ids = tuple(item.object_id for item in targets)
    topology_ids = {item.object_id for item in topology_blocks}
    selected_ids = {item.object_id for item in selected_blocks}
    if tuple(request.write_scope.section_ids) != tuple(request.targets):
        findings.append(
            _finding(
                "compile.scope_sections",
                "/write_scope/section_ids",
                "write scope section IDs must equal compile targets",
            )
        )
    scope_ids = set(request.write_scope.block_ids)
    topology_valid = (
        scope_ids == selected_ids
        and bool(scope_ids)
        and scope_ids <= topology_ids
        and (
            request.write_scope.level == "block"
            or scope_ids == topology_ids
        )
    )
    if not topology_valid:
        findings.append(
            _finding(
                "compile.scope_topology",
                "/write_scope/block_ids",
                "write scope block topology must equal target section topology",
            )
        )
    if set(target_ids) != set(request.targets):
        findings.append(
            _finding(
                "compile.scope_topology",
                "/request/targets",
                "compile targets do not resolve to the requested sections",
            )
        )
    expected_files = {
        binding.file_identity
        for binding in selected_bindings
        if binding.language in request.write_scope.languages
    }
    if set(request.write_scope.files) != expected_files:
        findings.append(
            _finding(
                "compile.scope_files",
                "/write_scope/files",
                "write scope files must equal explicit typed/raw bindings",
            )
        )
    allowed = set(request.write_scope.allowed_operations)
    for block in selected_blocks:
        operation = block.document.get("operation")
        block_allowed = set(_strings(block.document.get("allowed_operations")))
        if operation not in allowed or operation not in block_allowed:
            findings.append(
                _finding(
                    "compile.scope_operation",
                    f"/{block.object_id}/operation",
                    "planned block operation is outside the explicit write scope",
                    identity=block.identity,
                )
            )
    return findings


def _validate_move_placements(
    catalog: Mapping[str, LoadedCatalogObject],
    editorial: Mapping[str, object],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    selected_id = editorial.get("selected_story_id")
    selected = catalog.get(selected_id) if isinstance(selected_id, str) else None
    if selected is None or selected.object_type != "story" or selected.document.get("status") != "selected":
        return [
            _finding(
                "compile.story_selected",
                "/editorial/selected_story_id",
                "a selected story is required for materialization",
            )
        ]
    placements: dict[str, list[str]] = {}
    for section in catalog.values():
        if section.object_type != "section":
            continue
        bindings = section.document.get("move_bindings", ())
        if not isinstance(bindings, (list, tuple)):
            continue
        for binding in bindings:
            if (
                isinstance(binding, Mapping)
                and binding.get("role") == "primary"
                and isinstance(binding.get("move_id"), str)
            ):
                placements.setdefault(str(binding["move_id"]), []).append(
                    section.object_id
                )
    for index, move_id in enumerate(_strings(selected.document.get("argument_move_ids"))):
        if len(placements.get(move_id, ())) != 1:
            findings.append(
                _finding(
                    "compile.move_primary",
                    f"/{selected.object_id}/argument_move_ids/{index}",
                    "selected story move requires exactly one primary placement",
                )
            )
    return findings


def _approval_state(item: LoadedCatalogObject, kind: str) -> str:
    approvals = item.document.get("approvals", ())
    history = [
        approval
        for approval in approvals
        if isinstance(approval, Mapping) and approval.get("kind") == kind
    ] if isinstance(approvals, (list, tuple)) else []
    if not history:
        return "missing"
    current = [
        approval
        for approval in history
        if approval.get("object_revision") == item.revision
        and approval.get("object_hash") == item.semantic_hash
    ]
    if not current:
        return "stale"
    return "approved" if current[-1].get("decision") == "approved" else "rejected"


def _validate_approvals_and_gates(
    targets: tuple[LoadedCatalogObject, ...],
    closure: tuple[LoadedCatalogObject, ...],
    catalog: Mapping[str, LoadedCatalogObject],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for section in targets:
        state = _approval_state(section, "editorial_choice")
        if state != "approved":
            findings.append(
                _finding(
                    f"compile.plan_approval_{state}",
                    f"/{section.object_id}/approvals",
                    "section plan lacks a current approved editorial choice",
                    identity=section.identity,
                )
            )
    for claim in (item for item in closure if item.object_type == "claim"):
        state = _approval_state(claim, "scientific_scope")
        if state != "approved":
            findings.append(
                _finding(
                    f"compile.research_approval_{state}",
                    f"/{claim.object_id}/approvals",
                    "Research claim lacks a current approved scientific scope",
                    identity=claim.identity,
                )
            )
        gate_id = claim.document.get("gate_id")
        gate = catalog.get(gate_id) if isinstance(gate_id, str) else None
        if (
            claim.document.get("status") != "approved"
            or claim.document.get("gate_status") != "ready_to_write"
            or gate is None
            or gate.object_type != "scientific_gate"
            or gate.document.get("claim_id") != claim.object_id
            or gate.document.get("gate_decision") != "ready_to_write"
        ):
            findings.append(
                _finding(
                    "compile.research_gate",
                    f"/{claim.object_id}/gate_id",
                    "Research claim has not passed its current ready-to-write gate",
                    identity=claim.identity,
                )
            )
    return findings


def _privacy_findings(
    projections: Mapping[str, object],
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for name in sorted(projections):
        for hit in scan_private_material(
            projections[name],
            pointer=f"/{name}",
        ):
            findings.append(
                _finding(
                    "compile.privacy_private_material",
                    hit.pointer,
                    "Writer-facing projection contains private material",
                )
            )
    return findings


def _validate_citations(
    blocks: tuple[LoadedCatalogObject, ...],
    manuscript: ManuscriptSnapshot,
) -> list[CompileFinding]:
    registered = {
        key for bibliography in manuscript.bibliography_files for key in bibliography.entry_keys
    }
    findings: list[CompileFinding] = []
    for block in blocks:
        for index, key in enumerate(_strings(block.document.get("citation_keys"))):
            if key not in registered:
                findings.append(
                    _finding(
                        "compile.citation_missing",
                        f"/{block.object_id}/citation_keys/{index}",
                        "typed block citation is absent from the bibliography registry",
                        identity=block.identity,
                    )
                )
    return findings


def _prediction_state(
    manuscript: ManuscriptSnapshot,
    bindings: tuple[TexBlockBinding, ...],
    blocks: tuple[LoadedCatalogObject, ...],
    catalog: Mapping[str, LoadedCatalogObject],
) -> tuple[
    list[CompileFinding],
    tuple[AnalysisRequestSnapshot, ...],
    Mapping[str, tuple[str, ...]],
]:
    block_lookup = {
        (tex.identity, block.marker_id): block
        for tex in manuscript.tex_files
        for block in tex.blocks
    }
    inventories: dict[
        str,
        list[
            tuple[
                TexBlockBinding,
                frozenset[str],
                frozenset[str],
                bool,
                bool,
                bool,
            ]
        ],
    ] = {}
    for binding in bindings:
        block = block_lookup.get((binding.file_identity, binding.raw_block_id))
        if block is None:
            continue
        marker_id_sets = tuple(
            frozenset(marker.analysis_request_ids)
            for marker in block.inventory.predicted_markers
        )
        inventories.setdefault(binding.typed_block_id, []).append(
            (
                binding,
                frozenset(
                    marker.name for marker in block.inventory.predicted_markers
                ),
                frozenset().union(*marker_id_sets) if marker_id_sets else frozenset(),
                bool(marker_id_sets) and all(marker_id_sets),
                len(set(marker_id_sets)) <= 1,
                len(block.inventory.predicted_markers)
                == len(_PREDICTION_MARKERS),
            )
        )
    request_by_id = {
        item.request_id: item for item in manuscript.analysis_requests
    }
    findings: list[CompileFinding] = []
    used: dict[str, AnalysisRequestSnapshot] = {}
    normalized: dict[str, tuple[str, ...]] = {}
    for block_id in sorted(inventories):
        rows = inventories[block_id]
        if not any(row[1] for row in rows):
            continue
        binding_request_ids: list[frozenset[str]] = []
        for (
            binding,
            names,
            ids,
            ids_complete,
            ids_consistent,
            marker_count_exact,
        ) in rows:
            pointer = (
                f"/blocks/{block_id}/bindings/{binding.language}/"
                f"{binding.raw_block_id}"
            )
            if names != _PREDICTION_MARKERS or not marker_count_exact:
                findings.append(
                    _finding(
                        "compile.prediction_markers",
                        f"{pointer}/predicted_markers",
                        "each language binding of predicted material requires the complete marker set",
                        identity=binding.file_identity,
                    )
                )
            if not ids_complete:
                findings.append(
                    _finding(
                        "compile.prediction_areq",
                        f"{pointer}/analysis_request_ids",
                        "every predicted marker requires an analysis request in its marker body",
                        identity=binding.file_identity,
                    )
                )
            if not ids_consistent:
                findings.append(
                    _finding(
                        "compile.prediction_areq_mismatch",
                        f"{pointer}/analysis_request_ids",
                        "predicted markers in one binding must name the same analysis requests",
                        identity=binding.file_identity,
                    )
                )
            binding_request_ids.append(ids)
        if any(ids != binding_request_ids[0] for ids in binding_request_ids[1:]):
            findings.append(
                _finding(
                    "compile.prediction_areq_mismatch",
                    f"/blocks/{block_id}/analysis_request_ids",
                    "predicted material must use the same analysis requests in every language binding",
                )
            )
        ids = tuple(sorted(set().union(*binding_request_ids)))
        normalized[block_id] = ids
        for request_id in ids:
            request = request_by_id.get(request_id)
            if request is None:
                findings.append(
                    _finding(
                        "compile.prediction_areq",
                        f"/blocks/{block_id}/analysis_request_ids",
                        "predicted material references an absent analysis request",
                    )
                )
                continue
            used[request_id] = request
            if request.status not in _OPEN_ANALYSIS_REQUEST_STATUSES:
                findings.append(
                    _finding(
                        "compile.prediction_areq_status",
                        f"/blocks/{block_id}/analysis_request_ids",
                        "predicted material requires an open analysis request",
                        identity=request.identity,
                    )
                )
        block = next(
            (item for item in blocks if item.object_id == block_id),
            None,
        )
        gate_request_ids: set[str] = set()
        if block is not None:
            for claim_id in _strings(block.document.get("claim_refs")):
                claim = catalog.get(claim_id)
                gate_id = claim.document.get("gate_id") if claim is not None else None
                gate = catalog.get(gate_id) if isinstance(gate_id, str) else None
                if gate is not None and gate.object_type == "scientific_gate":
                    gate_request_ids.update(
                        _strings(gate.document.get("analysis_request_refs"))
                    )
        for request_id in ids:
            if request_id not in gate_request_ids:
                findings.append(
                    _finding(
                        "compile.prediction_gate_link",
                        f"/blocks/{block_id}/analysis_request_ids",
                        "predicted material requires an explicit link from its authorizing scientific gate",
                    )
                )
    return (
        findings,
        tuple(used[key] for key in sorted(used)),
        MappingProxyType({key: normalized[key] for key in sorted(normalized)}),
    )


def _block_projection(
    block: LoadedCatalogObject,
    bindings: tuple[TexBlockBinding, ...],
) -> dict[str, object]:
    return {
        "id": block.object_id,
        "section_id": block.document.get("section_id", ""),
        "reader_task": block.document.get("reader_task", ""),
        "operation": block.document.get("operation", ""),
        "allowed_operations": list(
            _strings(block.document.get("allowed_operations"))
        ),
        "ja_tex_block_id": block.document.get("ja_tex_block_id", ""),
        "en_tex_block_id": block.document.get("en_tex_block_id", ""),
        "claim_refs": list(_strings(block.document.get("claim_refs"))),
        "result_refs": list(_strings(block.document.get("result_refs"))),
        "source_refs": list(_strings(block.document.get("source_refs"))),
        "figure_refs": list(_strings(block.document.get("figure_refs"))),
        "citation_keys": list(_strings(block.document.get("citation_keys"))),
        "forbidden_scope_expansion": list(
            _strings(block.document.get("forbidden_scope_expansion"))
        ),
        "bindings": [
            binding.to_dict()
            for binding in bindings
            if binding.typed_block_id == block.object_id
        ],
    }


def _section_projection(
    section: LoadedCatalogObject,
    contract: ResolvedContract,
    closure: tuple[LoadedCatalogObject, ...],
    all_sections: tuple[LoadedCatalogObject, ...],
    blocks_by_id: Mapping[str, LoadedCatalogObject],
    bindings: tuple[TexBlockBinding, ...],
) -> dict[str, object]:
    target_index = all_sections.index(section)
    ordered_block_ids = _strings(section.document.get("ordered_block_ids"))
    block_rows = []
    for block_id in ordered_block_ids:
        block = blocks_by_id.get(block_id)
        if block is None:
            continue
        block_rows.append(_block_projection(block, bindings))
    return {
        "schema_version": 1,
        "reader_question": contract.effective.get("reader_question", ""),
        "section_purpose": contract.effective.get("purpose", ""),
        "connections": {
            "previous_section_id": (
                all_sections[target_index - 1].object_id if target_index > 0 else ""
            ),
            "next_section_id": (
                all_sections[target_index + 1].object_id
                if target_index + 1 < len(all_sections)
                else ""
            ),
        },
        "editorial_move_refs": list(
            _strings(section.document.get("editorial_move_refs"))
        ),
        "move_bindings": _json_compatible(
            section.document.get("move_bindings", ())
        ),
        "blocks": block_rows,
        "contract": {
            "section_kind": contract.section_kind,
            "snapshot_hash": contract.snapshot_hash,
            "effective": _json_compatible(contract.effective),
            "trace": _json_compatible(contract.trace),
            "layers": [item.to_dict() for item in contract.layers],
        },
        "section_fields": _section_field_projection(
            str(section.document.get("section_kind")),
            closure,
            contract,
        ),
        "extensions": {},
    }


def _packet_scope(
    request: CompileRequest,
    section: LoadedCatalogObject,
    blocks: tuple[LoadedCatalogObject, ...],
    bindings: tuple[TexBlockBinding, ...],
) -> WriteScope:
    block_ids = tuple(
        block.object_id
        for block in blocks
        if block.document.get("section_id") == section.object_id
    )
    bound_files = {
        binding.file_identity
        for binding in bindings
        if binding.typed_block_id in block_ids
        and binding.language in request.write_scope.languages
    }
    files = tuple(
        identity for identity in request.write_scope.files if identity in bound_files
    )
    return WriteScope(
        level=request.write_scope.level,
        languages=request.write_scope.languages,
        files=files,
        section_ids=(section.object_id,),
        block_ids=block_ids,
        allowed_operations=request.write_scope.allowed_operations,
    )


def materialize_compile(
    inputs: LoadedCompileInputs,
    contract_snapshot: CompileContractSnapshot,
    manuscript_snapshot: ManuscriptSnapshot,
    request: CompileRequest,
) -> CompileBundleCandidate:
    """Materialize validated inputs without reading or writing project files."""
    if not isinstance(inputs, LoadedCompileInputs):
        raise TypeError("inputs must be LoadedCompileInputs")
    if not isinstance(contract_snapshot, CompileContractSnapshot):
        raise TypeError("contract_snapshot must be CompileContractSnapshot")
    if not isinstance(manuscript_snapshot, ManuscriptSnapshot):
        raise TypeError("manuscript_snapshot must be ManuscriptSnapshot")
    if not isinstance(request, CompileRequest):
        raise TypeError("request must be CompileRequest")

    findings: list[CompileFinding] = []
    if inputs.source_mode != request.source_mode:
        findings.append(
            _finding(
                "compile.authority_source",
                "/source_mode",
                "loaded compile input source does not match the request",
            )
        )
    findings.extend(_readiness_findings(inputs))
    catalog, catalog_findings = _catalog_by_id(inputs.objects)
    findings.extend(catalog_findings)
    all_sections, all_manuscript_blocks, topology_findings = _manuscript_topology(
        inputs,
        catalog,
    )
    findings.extend(topology_findings)
    editorial = _editorial_document(inputs)
    if editorial is None:
        editorial = {}
        findings.append(
            _finding(
                "compile.story_missing",
                "/editorial",
                "validated Editorial aggregate is missing",
            )
        )
    findings.extend(_validate_typed_seeds(catalog, editorial, request.targets))
    context_closure, closure_findings = _dependency_closure(
        catalog,
        _seed_ids(editorial, request.targets),
    )
    findings.extend(closure_findings)
    selected_story_id = editorial.get("selected_story_id")
    selected_story = (
        catalog.get(selected_story_id)
        if isinstance(selected_story_id, str)
        else None
    )
    selected_move_ids = frozenset(
        _strings(selected_story.document.get("argument_move_ids"))
        if selected_story is not None and selected_story.object_type == "story"
        else ()
    )
    authoring_closure, authoring_findings = _dependency_closure(
        catalog,
        _authoring_seed_ids(editorial, request.targets),
        allowed_move_ids=selected_move_ids,
    )
    findings.extend(authoring_findings)
    findings.extend(_validate_declared_dependencies(context_closure, catalog))

    targets = tuple(
        catalog[target]
        for target in request.targets
        if target in catalog and catalog[target].object_type == "section"
    )
    topology_blocks = tuple(
        item
        for section in targets
        for block_id in _strings(section.document.get("ordered_block_ids"))
        if (item := catalog.get(block_id)) is not None and item.object_type == "block"
    )
    selected_block_ids = (
        set(request.write_scope.block_ids)
        if request.write_scope.level == "block"
        else {item.object_id for item in topology_blocks}
    )
    blocks = tuple(
        item for item in topology_blocks if item.object_id in selected_block_ids
    )
    findings.extend(_validate_section_invariants(targets, catalog))
    findings.extend(_validate_contracts(contract_snapshot, targets))
    findings.extend(manuscript_snapshot.findings)
    binding_result = bind_typed_tex_blocks(
        manuscript_snapshot,
        tuple(block.document for block in all_manuscript_blocks),
    )
    findings.extend(binding_result.findings)
    all_bindings = binding_result.bindings
    bindings = tuple(
        binding
        for binding in all_bindings
        if binding.typed_block_id in selected_block_ids
    )
    findings.extend(
        _validate_scope(
            request,
            targets,
            topology_blocks,
            blocks,
            bindings,
        )
    )
    findings.extend(_validate_move_placements(catalog, editorial))
    findings.extend(
        _validate_approvals_and_gates(targets, authoring_closure, catalog)
    )
    findings.extend(_validate_citations(blocks, manuscript_snapshot))
    prediction_findings, analysis_requests, predicted_by_block = _prediction_state(
        manuscript_snapshot,
        bindings,
        blocks,
        catalog,
    )
    findings.extend(prediction_findings)

    global_context: dict[str, object] = {}
    projections: dict[str, dict[str, object]] = {}
    claims = [
        _object_projection(
            item,
            (
                "statement",
                "warrant",
                "scope",
                "limitation",
                "not_claiming",
            ),
        )
        for item in authoring_closure
        if item.object_type == "claim"
    ]
    evidence = _evidence_projection(authoring_closure)
    privacy_sources: dict[str, object] = {
        "approved_claims": claims,
        "evidence": evidence,
    }
    if not any(finding.severity == "error" for finding in findings):
        global_context = _global_context(
            editorial,
            catalog,
            all_sections,
            {block.object_id: block for block in all_manuscript_blocks},
            all_bindings,
            manuscript_snapshot,
        )
        blocks_by_id = {
            block.object_id: block for block in all_manuscript_blocks
        }
        projections = {
            section.object_id: _section_projection(
                section,
                contract_snapshot.contracts[
                    str(section.document["section_kind"])
                ],
                authoring_closure,
                all_sections,
                blocks_by_id,
                all_bindings,
            )
            for section in targets
        }
        privacy_sources.update(
            {
                "global_context": global_context,
                "section_projections": projections,
            }
        )
    findings.extend(_privacy_findings(privacy_sources))

    context_objects = {item.object_id: item for item in context_closure}
    context_objects.update({item.object_id: item for item in all_sections})
    context_objects.update(
        {item.object_id: item for item in all_manuscript_blocks}
    )
    materialized_inputs = _compile_inputs(
        inputs,
        contract_snapshot,
        manuscript_snapshot,
        tuple(
            sorted(
                context_objects.values(),
                key=lambda item: (
                    item.model_name,
                    item.object_type,
                    item.object_id,
                ),
            )
        ),
        all_bindings,
        analysis_requests,
        target_section_ids=frozenset(request.targets),
        write_block_ids=frozenset(selected_block_ids),
    )
    stable = _stable_findings(findings)
    has_error = any(finding.severity == "error" for finding in stable)
    if has_error:
        compile_id = compute_compile_id(
            compiler_contract_version=_COMPILER_CONTRACT_VERSION,
            source_mode=inputs.source_mode,
            applicable=inputs.applicable,
            request=request,
            authority=inputs.authority,
            inputs=materialized_inputs,
            contract_snapshot_hash=contract_snapshot.snapshot_hash,
            manuscript_snapshot_hash=manuscript_snapshot.snapshot_hash,
            global_context={},
            section_projections={},
        )
        return CompileBundleCandidate(
            compiler_contract_version=_COMPILER_CONTRACT_VERSION,
            compile_id=compile_id,
            status="blocked",
            source_mode=inputs.source_mode,
            applicable=inputs.applicable,
            request=request,
            authority=inputs.authority,
            inputs=materialized_inputs,
            global_context={},
            section_plans=(),
            writer_packets=(),
            findings=stable,
            contract_snapshot_hash=contract_snapshot.snapshot_hash,
            manuscript_snapshot_hash=manuscript_snapshot.snapshot_hash,
        )

    compile_id = compute_compile_id(
        compiler_contract_version=_COMPILER_CONTRACT_VERSION,
        source_mode=inputs.source_mode,
        applicable=inputs.applicable,
        request=request,
        authority=inputs.authority,
        inputs=materialized_inputs,
        contract_snapshot_hash=contract_snapshot.snapshot_hash,
        manuscript_snapshot_hash=manuscript_snapshot.snapshot_hash,
        global_context=global_context,
        section_projections=projections,
    )
    plans = tuple(
        SectionPlan(
            section_id=section.object_id,
            revision=section.revision,
            semantic_hash=section.semantic_hash,
            section_kind=str(section.document["section_kind"]),
            ordered_block_ids=_strings(section.document.get("ordered_block_ids")),
            inputs=materialized_inputs,
            projection=projections[section.object_id],
        )
        for section in targets
    )
    plan_by_id = {plan.section_id: plan for plan in plans}
    citation_registry = global_context["citation_registry"]
    prohibitions = global_context["terminology"]["prohibitions"]
    packets: list[WriterPacket] = []
    for section in targets:
        packet_scope = _packet_scope(request, section, blocks, bindings)
        plan = plan_by_id[section.object_id]
        plan_dict = plan.to_dict()
        target_blocks = [
            row
            for row in projections[section.object_id]["blocks"]
            if row["id"] in packet_scope.block_ids
        ]
        prediction_ids = tuple(
            sorted(
                {
                    request_id
                    for block_id in packet_scope.block_ids
                    for request_id in predicted_by_block.get(block_id, ())
                }
            )
        )
        request_identities = {
            request.identity
            for request in analysis_requests
            if request.request_id in prediction_ids
        }
        prediction_snapshots = [
            request.to_dict()
            for request in analysis_requests
            if request.request_id in prediction_ids
        ]
        packet_inputs = tuple(
            item
            for item in materialized_inputs
            if item.input_type != "analysis-request"
            or item.identity in request_identities
        )
        dependency_profile = {
            "schema_version": 1,
            "input_count": len(packet_inputs),
            "relations": sorted({item.relation for item in packet_inputs}),
            "extensions": {},
        }
        dependency_hash = semantic_hash(
            [item.to_dict() for item in packet_inputs]
        )
        forbidden_assertions = sorted(
            {
                text
                for claim in claims
                for text in _strings(claim.get("not_claiming"))
            }
            | {
                text
                for row in target_blocks
                for text in _strings(row.get("forbidden_scope_expansion"))
            }
        )
        packets.append(
            WriterPacket(
                packet_id=_packet_id(
                    compile_id,
                    section.object_id,
                    packet_scope.to_dict(),
                ),
                compile_id=compile_id,
                authority=inputs.authority,
                write_scope=packet_scope,
                inputs=packet_inputs,
                read_context={
                    "schema_version": 1,
                    "global": f".paperops/compile/{compile_id}/context/global.json",
                    "global_context_hash": semantic_hash(global_context),
                    "manuscript_files": [
                        item.to_dict()
                        for item in manuscript_snapshot.read_files
                        if not item.identity.startswith(
                            "_paperops/model/issues/analysis/"
                        )
                        or item.identity in request_identities
                    ],
                    "extensions": {},
                },
                payload={
                    "schema_version": 1,
                    "section_plan": {
                        "id": section.object_id,
                        "path": (
                            f".paperops/compile/{compile_id}/plans/"
                            f"{section.object_id}.json"
                        ),
                        "content_hash": semantic_hash(plan_dict),
                        "semantic_hash": section.semantic_hash,
                    },
                    "target_section_id": section.object_id,
                    "target_blocks": target_blocks,
                    "selected_story_id": editorial.get("selected_story_id", ""),
                    "ordered_move_ids": list(
                        _strings(
                            catalog[str(editorial.get("selected_story_id"))].document.get(
                                "argument_move_ids"
                            )
                        )
                    ),
                    "approved_claims": claims,
                    "evidence": evidence,
                    "citation_registry": citation_registry,
                    "contract_snapshot_hash": contract_snapshot.contracts[
                        str(section.document["section_kind"])
                    ].snapshot_hash,
                    "terminology_prohibitions": prohibitions,
                    "forbidden_assertions": forbidden_assertions,
                    "predicted_result": {
                        "enabled": bool(prediction_ids),
                        "analysis_request_ids": list(prediction_ids),
                        "analysis_requests": prediction_snapshots,
                    },
                    "extensions": {},
                },
                dependency_profile=dependency_profile,
                dependency_hash=dependency_hash,
            )
        )
    packets.sort(key=lambda packet: packet.packet_id)
    return CompileBundleCandidate(
        compiler_contract_version=_COMPILER_CONTRACT_VERSION,
        compile_id=compile_id,
        status="ready",
        source_mode=inputs.source_mode,
        applicable=inputs.applicable,
        request=request,
        authority=inputs.authority,
        inputs=materialized_inputs,
        global_context=global_context,
        section_plans=plans,
        writer_packets=tuple(packets),
        findings=stable,
        contract_snapshot_hash=contract_snapshot.snapshot_hash,
        manuscript_snapshot_hash=manuscript_snapshot.snapshot_hash,
    )


__all__ = [
    "CompileBundleCandidate",
    "CompileContractSnapshot",
    "compute_compile_id",
    "materialize_compile",
]
