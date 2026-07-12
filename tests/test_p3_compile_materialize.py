from __future__ import annotations

import copy
import json
import shutil
import tempfile
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import yaml

from tests.helpers import ROOT


sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops.compiler import (  # noqa: E402
    CompileBundle,
    CompileBundleCandidate,
    CompileContractSnapshot,
    CompileFinding,
    CompileRequest,
    InputSnapshot,
    WriteScope,
    materialize_compile,
    resolve_section_contract,
    scan_manuscript,
)
from paperops.compiler.inputs import (  # noqa: E402
    LoadedCatalogObject,
    load_compile_inputs,
)
from paperops.compiler.types import _json_compatible  # noqa: E402
from paperops.compiler.materialize import (  # noqa: E402
    _input_type,
)
from paperops.model_validation import run_model_hash  # noqa: E402
from paperops_schema import (  # noqa: E402
    load_document as load_schema_document,
    semantic_hash as model_semantic_hash,
    validate_schema,
)
from tests import test_issue_model as issue_fixtures  # noqa: E402
from tests import test_research_migration_adapter as research_fixtures  # noqa: E402
from tests.helpers import run_cli, run_python_script  # noqa: E402
from tests.test_p3_compile_inputs import CHECKER, tracked_tree_snapshot  # noqa: E402
from tests.test_p3_manuscript_contract import (  # noqa: E402
    add_current_editorial_approval,
    valid_block,
    valid_section,
)
from tests.test_paperops_model_check import valid_documents  # noqa: E402
from tests.test_research_model import (  # noqa: E402
    claim as research_claim,
    figure as research_figure,
    gate as research_gate,
    result as research_result,
    source as research_source,
)


HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")
FIXED_TRANSACTIONS = (
    "model-20260712T000001000001Z-111111111111",
    "model-20260712T000002000002Z-222222222222",
    "model-20260712T000003000003Z-333333333333",
)
PREDICTION_TRANSACTIONS = (
    "model-20260712T000004000004Z-444444444444",
    "model-20260712T000005000005Z-555555555555",
    "model-20260712T000006000006Z-666666666666",
    "model-20260712T000007000007Z-777777777777",
)


def _approved_research_documents(
    approval_note: str,
    *,
    analysis_request_refs: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    claim = research_claim()
    claim["manuscript_block_refs"] = []
    claim["visual_obligation_refs"] = []
    claim["approvals"] = []
    claim_hash = model_semantic_hash(claim, excluded_paths=HASH_EXCLUSIONS)
    claim["approvals"] = [
        {
            "approval_id": "APR-0001",
            "kind": "scientific_scope",
            "decision": "approved",
            "object_revision": 1,
            "object_hash": claim_hash,
            "actor": "human",
            "note": approval_note,
        }
    ]

    result = research_result()
    result["manuscript_block_refs"] = []
    figure = research_figure()
    figure["manuscript_block_refs"] = []
    figure["visual_obligation_refs"] = []
    source = research_source()
    source["manuscript_block_refs"] = []
    gate = research_gate()
    gate["analysis_request_refs"] = list(analysis_request_refs)
    gate["external_validation_gates"] = []
    gate["central_assumptions"][0]["manuscript_block_refs"] = []
    return [claim, result, figure, source, gate]


def _adopt(project: Path, model: str) -> str:
    code, raw, error = run_cli(["model", "diff", model, str(project), "--json"])
    if code != 0:
        raise AssertionError(error or raw)
    transaction_id = str(json.loads(raw)["transaction_id"])
    code, raw, error = run_cli(
        ["model", "adopt", model, str(project), "--yes", "--json"]
    )
    if code != 0:
        raise AssertionError(error or raw)
    return transaction_id


def _object_hash(project: Path, model: str, object_id: str) -> str:
    result = run_model_hash(project, model, object_id)
    if not result.ok:
        raise AssertionError(result.findings)
    return result.hashes[object_id]


def _dependency(
    project: Path,
    model: str,
    object_id: str,
    relation: str,
    *,
    revision: int | None = 1,
) -> dict[str, object]:
    result: dict[str, object] = {
        "target_id": object_id,
        "relation": relation,
        "expected_hash": _object_hash(project, model, object_id),
    }
    if revision is not None:
        result["expected_revision"] = revision
    return result


def _editorial_documents() -> tuple[dict[str, object], dict[str, object]]:
    editorial, hierarchy = valid_documents()
    editorial["story_candidates"][0].update(
        {
            "thesis": "A controlled comparison supports a bounded mechanism.",
            "argument_move_ids": ["MOV-0001", "MOV-0002", "MOV-0003"],
            "result_order": ["RHI-0001"],
        }
    )
    editorial["story_candidates"][1].update(
        {
            "thesis": "An alternative inventory-led explanation.",
            "argument_move_ids": ["MOV-0004"],
            "result_order": ["RHI-0001"],
            "rejection_reason": "It obscures the controlled comparison.",
        }
    )
    editorial["claim_roles"]["foreground"] = {
        "claim_ids": ["CLM-0001"],
        "none_reason": "",
    }
    editorial["argument_moves"] = [
        {
            "id": "MOV-0001",
            "position": 1,
            "stance": "assert",
            "reader_question": "How is the comparison defined?",
            "assertion": "The method isolates the controlled comparison.",
            "claim_ids": ["CLM-0001"],
            "result_item_ids": ["RHI-0001"],
            "next_move_id": "MOV-0002",
        },
        {
            "id": "MOV-0002",
            "position": 2,
            "stance": "assert",
            "reader_question": "What changes under control?",
            "assertion": "The measured response differs from the comparator.",
            "claim_ids": ["CLM-0001"],
            "result_item_ids": ["RHI-0001"],
            "next_move_id": "MOV-0003",
        },
        {
            "id": "MOV-0003",
            "position": 3,
            "stance": "boundary",
            "reader_question": "What does the result mean within scope?",
            "assertion": "The mechanism remains bounded to the validated regime.",
            "claim_ids": ["CLM-0001"],
            "result_item_ids": ["RHI-0001"],
            "next_move_id": "MOV-0004",
        },
        {
            "id": "MOV-0004",
            "position": 4,
            "stance": "reject",
            "reader_question": "Should run inventory organize the paper?",
            "assertion": "Run inventory does not expose the controlled comparison.",
            "claim_ids": [],
            "result_item_ids": ["RHI-0001"],
            "next_move_id": "",
        },
    ]
    editorial["visual_obligations"] = [
        {
            "id": "VIS-0001",
            "reader_task": "Compare treatment and control.",
            "takeaway": "The controlled response differs within scope.",
            "claim_ids": ["CLM-0001"],
            "preferred_form": "paired plot",
            "status": "satisfied",
            "waiver_reason": "",
            "figure_ids": ["FIG-0001"],
        }
    ]
    return editorial, hierarchy


def _manuscript_records(project: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    specifications = (
        (
            "SEC-0001",
            "BLK-0001",
            "methods",
            "MOV-0001",
            "method.structure.01",
            ("CLM-0001", "RES-0001", "SRC-0001", "GATE-0001"),
        ),
        (
            "SEC-0002",
            "BLK-0002",
            "results",
            "MOV-0002",
            "results.traceability.01",
            ("CLM-0001", "RES-0001", "FIG-0001"),
        ),
        (
            "SEC-0003",
            "BLK-0003",
            "discussion",
            "MOV-0003",
            "discussion.scope.01",
            ("CLM-0001", "RES-0001", "SRC-0001", "GATE-0001"),
        ),
    )
    research_types = {
        "CLM-0001": "claim",
        "RES-0001": "result",
        "SRC-0001": "source",
        "FIG-0001": "figure",
        "GATE-0001": "scientific_gate",
    }
    sections: list[dict[str, object]] = []
    blocks: list[dict[str, object]] = []
    for section_id, block_id, kind, move_id, marker, research_ids in specifications:
        section = valid_section(section_id, move_id=move_id)
        section.update(
            {
                "section_kind": kind,
                "ordered_block_ids": [block_id],
                "contract_refs": [f"contract:{kind}"],
                "editorial_move_refs": [move_id],
                "move_bindings": [
                    {
                        "move_id": move_id,
                        "role": "primary",
                        "reason": f"Primary {kind} placement.",
                    }
                ],
                "research_refs": list(research_ids),
                "mirror_policy": "paired",
            }
        )
        if section_id == "SEC-0002":
            section["editorial_move_refs"] = ["MOV-0001", move_id]
            section["move_bindings"] = [
                {
                    "move_id": "MOV-0001",
                    "role": "echo",
                    "reason": "Recall the comparison before the result.",
                },
                {
                    "move_id": move_id,
                    "role": "primary",
                    "reason": "Primary results placement.",
                },
            ]
        section["dependencies"] = [
            *[
                _dependency(project, "editorial", ref, "guided_by", revision=None)
                for ref in section["editorial_move_refs"]
            ],
            *[
                _dependency(project, "research", ref, "uses")
                for ref in research_ids
            ],
        ]
        add_current_editorial_approval(section)

        block = valid_block()
        block.update(
            {
                "id": block_id,
                "section_id": section_id,
                "block_kind": "method" if kind == "methods" else "evidence",
                "reader_task": f"Fulfil the approved {kind} reader task.",
                "operation": "rewrite",
                "ja_tex_block_id": marker,
                "en_tex_block_id": marker,
                "claim_refs": ["CLM-0001"],
                "result_refs": ["RES-0001"],
                "source_refs": ["SRC-0001"] if "SRC-0001" in research_ids else [],
                "figure_refs": ["FIG-0001"] if "FIG-0001" in research_ids else [],
                "citation_keys": ["example2026"],
                "allowed_operations": ["rewrite"],
                "forbidden_scope_expansion": ["unapproved universal claim"],
            }
        )
        block_refs = [
            *block["claim_refs"],
            *block["result_refs"],
            *block["source_refs"],
            *block["figure_refs"],
        ]
        block["dependencies"] = [
            _dependency(project, "research", ref, "supports")
            for ref in block_refs
        ]
        sections.append(section)
        blocks.append(block)
    return sections, blocks


def _render_issue_card(document: dict[str, object]) -> str:
    value = copy.deepcopy(document)
    value.pop("schema_version", None)
    record_type = value.pop("record_type")
    metadata = value.pop("metadata")
    lines = ["---", f"type: {record_type}"]
    for key, item in value.items():
        lines.append(
            f"{key}: {json.dumps(item, ensure_ascii=False, separators=(',', ':'))}"
        )
    lines.extend(
        [
            f"created: {metadata['created_at']}",
            f"updated: {metadata['updated_at']}",
            "---",
            "",
        ]
    )
    return "\n".join(lines)


def _write_prediction_issue_sources(
    project: Path,
    request_ids: tuple[str, ...],
) -> None:
    roots = (
        project / "_paperops/review/feedback",
        project / "_paperops/requests/analysis",
        project / "_paperops/requests/writing",
        project / "_paperops/review/responses",
        project / "_paperops/review/rounds",
    )
    for root in roots:
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)

    feedback = issue_fixtures.feedback()
    feedback.update(
        {
            "review_round_ref": "RVW-0001",
            "targets": [],
            "related_issue_refs": [],
            "related_block_refs": [],
        }
    )
    (roots[0] / "FB-0001.md").write_text(
        _render_issue_card(feedback),
        encoding="utf-8",
    )
    review_round = issue_fixtures.review_round()
    review_round.update(
        {
            "targets": [],
            "related_issue_refs": [],
            "related_block_refs": [],
        }
    )
    review_round["delegation_ledger"] = []
    (roots[4] / "RVW-0001.md").write_text(
        _render_issue_card(review_round),
        encoding="utf-8",
    )
    for request_id in request_ids:
        request = issue_fixtures.analysis_request("planned")
        request.update(
            {
                "id": request_id,
                "review_round_ref": "RVW-0001",
                "targets": [],
                "related_issue_refs": [],
                "related_block_refs": [],
                "requested_by": "FB-0001",
                "related_claim_refs": [],
                "related_result_refs": [],
                "manuscript_refs": [],
                "requested_outputs": [],
            }
        )
        request["prediction"]["state"] = "none"
        request["prediction"]["basis_source_refs"] = []
        request["execution_provenance"]["result_refs"] = []
        request["execution_provenance"]["figure_refs"] = []
        (roots[1] / f"{request_id}.md").write_text(
            _render_issue_card(request),
            encoding="utf-8",
        )


def _prebind_gate_hash(
    project: Path,
    analysis_request_refs: tuple[str, ...],
) -> None:
    gate_document = next(
        item
        for item in _approved_research_documents(
            "Approved for compile.",
            analysis_request_refs=analysis_request_refs,
        )
        if item["record_type"] == "scientific_gate"
    )
    gate_hash = model_semantic_hash(
        gate_document,
        excluded_paths=HASH_EXCLUSIONS,
    )
    gate_source = project / "_paperops/claims/gates/GATE-0001.md"
    source_text = gate_source.read_text(encoding="utf-8")
    replaced = source_text.replace(
        "analysis_request_refs: []",
        "analysis_request_refs: "
        + json.dumps(list(analysis_request_refs), separators=(",", ":")),
    )
    if replaced == source_text:
        raise AssertionError("Research gate source lacks analysis_request_refs")
    gate_source.write_text(replaced, encoding="utf-8")

    manifest_path = project / "_paperops/contracts/manuscript-migration.yml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for section in manifest["sections"]:
        for dependency in section["dependencies"]:
            if dependency["target_id"] == "GATE-0001":
                dependency["expected_hash"] = gate_hash
        section_hash = model_semantic_hash(
            section,
            excluded_paths=HASH_EXCLUSIONS,
        )
        for approval in section["approvals"]:
            if approval["kind"] == "editorial_choice":
                approval["object_hash"] = section_hash
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    index_path = project / "_paperops/model/manuscript/index.yml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    for row in index["records"]:
        if row["record_type"] != "section":
            continue
        path = project / row["document"]
        section = yaml.safe_load(path.read_text(encoding="utf-8"))
        for dependency in section["dependencies"]:
            if dependency["target_id"] == "GATE-0001":
                dependency["expected_hash"] = gate_hash
        section_hash = model_semantic_hash(
            section,
            excluded_paths=HASH_EXCLUSIONS,
        )
        for approval in section["approvals"]:
            if approval["kind"] == "editorial_choice":
                approval["object_hash"] = section_hash
        row["expected_hash"] = section_hash
        path.write_text(
            yaml.safe_dump(section, sort_keys=False),
            encoding="utf-8",
        )
    index_path.write_text(
        yaml.safe_dump(index, sort_keys=False),
        encoding="utf-8",
    )


def approved_project(
    parent: Path,
    *,
    approval_note: str = "Approved for compile.",
    analysis_request_refs: tuple[str, ...] = (),
) -> Path:
    project = research_fixtures.ResearchMigrationAdapterTest().project(
        parent,
        _approved_research_documents(approval_note),
    )
    with patch(
        "paperops.cli.model_commands.new_transaction_id",
        side_effect=FIXED_TRANSACTIONS,
    ):
        _adopt(project, "research")

        editorial, hierarchy = _editorial_documents()
        editorial_root = project / "_paperops/model/editorial"
        (editorial_root / "editorial-model.yml").write_text(
            yaml.safe_dump(editorial, sort_keys=False),
            encoding="utf-8",
        )
        (editorial_root / "results-hierarchy.yml").write_text(
            yaml.safe_dump(hierarchy, sort_keys=False),
            encoding="utf-8",
        )
        storyline = project / "_paperops/notes/views/storyline.md"
        if storyline.exists():
            storyline.unlink()
        _adopt(project, "editorial")

        sections, blocks = _manuscript_records(project)
        manifest = project / "_paperops/contracts/manuscript-migration.yml"
        manifest.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "marker_check": True,
                    "sections": sections,
                    "blocks": blocks,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        references = project / "manuscript/shared/bib/references.bib"
        references.write_text(
            "@article{example2026,\n"
            "  author = {Example, Ada},\n"
            "  title = {A public controlled comparison},\n"
            "  year = {2026}\n"
            "}\n",
            encoding="utf-8",
        )
        _adopt(project, "manuscript")
    if analysis_request_refs:
        with patch(
            "paperops.cli.model_commands.new_transaction_id",
            side_effect=PREDICTION_TRANSACTIONS,
        ):
            _write_prediction_issue_sources(project, analysis_request_refs)
            _adopt(project, "issue")
            _prebind_gate_hash(project, analysis_request_refs)
            _adopt(project, "research")
            _adopt(project, "manuscript")
    return project


def approved_request() -> CompileRequest:
    return CompileRequest(
        targets=("SEC-0001", "SEC-0002", "SEC-0003"),
        write_scope=WriteScope(
            level="manuscript",
            languages=("ja", "en"),
            files=(
                "manuscript/ja/sections/20_method.tex",
                "manuscript/en/sections/20_method.tex",
                "manuscript/ja/sections/30_results.tex",
                "manuscript/en/sections/30_results.tex",
                "manuscript/ja/sections/40_discussion.tex",
                "manuscript/en/sections/40_discussion.tex",
            ),
            section_ids=("SEC-0001", "SEC-0002", "SEC-0003"),
            block_ids=("BLK-0001", "BLK-0002", "BLK-0003"),
            allowed_operations=("rewrite",),
        ),
    )


def mutated_loaded_object(
    loaded,
    object_id: str,
    mutation,
):
    objects: list[LoadedCatalogObject] = []
    for item in loaded.objects:
        if item.object_id != object_id:
            objects.append(item)
            continue
        document = _json_compatible(item.document)
        mutation(document)
        exclusions = (
            HASH_EXCLUSIONS
            if item.object_type
            in {
                "section",
                "block",
                "claim",
                "result",
                "source",
                "figure",
                "scientific_gate",
            }
            else ()
        )
        objects.append(
            replace(
                item,
                semantic_hash=model_semantic_hash(
                    document,
                    excluded_paths=exclusions,
                ),
                content_hash=model_semantic_hash(document),
                document=document,
            )
        )
    return replace(loaded, objects=tuple(objects), snapshot_hash=HASH_B)


class P3ApprovedCompileFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))
        cls.request = approved_request()
        cls.loaded = load_compile_inputs(cls.project, cls.request)
        cls.contracts = CompileContractSnapshot.from_contracts(
            resolve_section_contract(cls.project, kind)
            for kind in ("methods", "results", "discussion")
        )
        cls.manuscript = scan_manuscript(cls.project)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_fixture_uses_real_p2_authority_and_is_compile_ready(self) -> None:
        before = tracked_tree_snapshot(self.project)

        loaded = self.loaded
        contracts = self.contracts
        manuscript = self.manuscript

        self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)
        self.assertTrue(loaded.applicable)
        self.assertEqual(
            {authority.mode for authority in loaded.authority},
            {"v2-authoritative"},
        )
        self.assertEqual(
            {item.object_type for item in loaded.objects},
            {
                "block",
                "claim",
                "figure",
                "move",
                "result",
                "results_item",
                "scientific_gate",
                "section",
                "source",
                "story",
                "visual",
            },
        )
        self.assertFalse(
            [
                finding
                for contract in contracts.contracts.values()
                for finding in contract.findings
                if finding.severity == "error"
            ]
        )
        self.assertFalse(
            [finding for finding in manuscript.findings if finding.severity == "error"]
        )
        self.assertEqual(tracked_tree_snapshot(self.project), before)

    def test_approved_fixture_materializes_exact_global_plans_packets_and_inputs(
        self,
    ) -> None:
        before = tracked_tree_snapshot(self.project)

        candidate = materialize_compile(
            self.loaded,
            self.contracts,
            self.manuscript,
            self.request,
        )
        repeated = materialize_compile(
            self.loaded,
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        self.assertEqual(candidate.to_dict(), repeated.to_dict())
        self.assertRegex(candidate.compile_id, r"^compile-v1-[0-9a-f]{64}$")
        self.assertEqual(candidate.contract_snapshot_hash, self.contracts.snapshot_hash)
        self.assertEqual(
            candidate.manuscript_snapshot_hash,
            self.manuscript.snapshot_hash,
        )
        self.assertTrue(candidate.applicable)
        self.assertEqual(candidate.source_mode, "authoritative")

        global_context = candidate.to_dict()["global_context"]
        self.assertEqual(
            set(global_context),
            {
                "schema_version",
                "reader_transformation",
                "selected_story",
                "rejected_stories",
                "thesis",
                "claim_roles",
                "evidence_ladder",
                "ordered_moves",
                "section_block_map",
                "salience",
                "visual_obligations",
                "terminology",
                "mirror_policy",
                "manuscript_read_files",
                "citation_registry",
                "extensions",
            },
        )
        self.assertEqual(global_context["selected_story"]["id"], "STY-0001")
        self.assertEqual(
            set(global_context["selected_story"]),
            {
                "id",
                "label",
                "thesis",
                "result_order",
                "argument_move_ids",
                "selection_reason",
            },
        )
        self.assertEqual(
            [story["id"] for story in global_context["rejected_stories"]],
            ["STY-0002"],
        )
        self.assertEqual(
            [move["id"] for move in global_context["ordered_moves"]],
            ["MOV-0001", "MOV-0002", "MOV-0003"],
        )
        self.assertEqual(
            global_context["ordered_moves"][-1]["next_move_id"],
            "",
        )
        self.assertTrue(
            all(
                set(move)
                == {
                    "id",
                    "position",
                    "stance",
                    "reader_question",
                    "assertion",
                    "claim_ids",
                    "result_item_ids",
                    "next_move_id",
                }
                for move in global_context["ordered_moves"]
            )
        )
        self.assertTrue(
            all(
                set(visual)
                == {
                    "id",
                    "reader_task",
                    "takeaway",
                    "claim_ids",
                    "preferred_form",
                    "status",
                    "waiver_reason",
                    "figure_ids",
                }
                for visual in global_context["visual_obligations"]
            )
        )
        self.assertEqual(global_context["thesis"], global_context["selected_story"]["thesis"])
        self.assertEqual(
            [row["section_id"] for row in global_context["section_block_map"]],
            ["SEC-0001", "SEC-0002", "SEC-0003"],
        )
        self.assertEqual(
            global_context["citation_registry"],
            [
                {
                    "identity": "manuscript/shared/bib/mypapers.bib",
                    "content_hash": next(
                        item.content_hash
                        for item in self.manuscript.bibliography_files
                        if item.identity == "manuscript/shared/bib/mypapers.bib"
                    ),
                    "entry_keys": [],
                },
                {
                    "identity": "manuscript/shared/bib/references.bib",
                    "content_hash": next(
                        item.content_hash
                        for item in self.manuscript.bibliography_files
                        if item.identity == "manuscript/shared/bib/references.bib"
                    ),
                    "entry_keys": ["example2026"],
                },
            ],
        )
        self.assertEqual(
            [row["identity"] for row in global_context["manuscript_read_files"]],
            sorted(row["identity"] for row in global_context["manuscript_read_files"]),
        )

        self.assertEqual(
            [(plan.section_id, plan.section_kind) for plan in candidate.section_plans],
            [
                ("SEC-0001", "methods"),
                ("SEC-0002", "results"),
                ("SEC-0003", "discussion"),
            ],
        )
        self.assertEqual(len(candidate.writer_packets), 3)
        self.assertEqual(
            [packet.packet_id for packet in candidate.writer_packets],
            sorted(packet.packet_id for packet in candidate.writer_packets),
        )
        self.assertTrue(all(packet.dependency_hash for packet in candidate.writer_packets))
        self.assertTrue(
            all(packet.dependency_profile for packet in candidate.writer_packets)
        )
        plans = {plan.section_kind: plan.to_dict()["projection"] for plan in candidate.section_plans}
        self.assertEqual(
            set(plans["methods"]["section_fields"]),
            {
                "estimand",
                "unit_of_analysis",
                "baseline_or_comparator",
                "decision_criteria",
                "verification_or_convergence",
                "main_text",
                "supplement",
                "citation",
                "code_or_manifest",
            },
        )
        self.assertEqual(
            set(plans["discussion"]["section_fields"]),
            {
                "observation",
                "inference",
                "mechanism",
                "alternative",
                "implication",
                "prediction",
                "limitation",
            },
        )
        self.assertEqual(
            plans["methods"]["section_fields"]["estimand"][0]["value"],
            "Mean controlled response.",
        )
        self.assertEqual(
            plans["methods"]["section_fields"]["citation"]["sources"][0][
                "citation_keys"
            ],
            ["example2026"],
        )
        self.assertEqual(
            plans["discussion"]["section_fields"]["inference"][0]["statement"],
            "The controlled comparison supports the bounded mechanism.",
        )
        self.assertEqual(
            plans["discussion"]["section_fields"]["mechanism"][0]["warrant"],
            "The comparator isolates the tested effect.",
        )

        compile_snapshots = [
            item for item in candidate.inputs if item.input_type == "compile-snapshot"
        ]
        self.assertEqual(len(compile_snapshots), 1)
        self.assertEqual(compile_snapshots[0].snapshot_kind, "content")
        self.assertEqual(compile_snapshots[0].semantic_hash, self.loaded.snapshot_hash)
        catalog_inputs = [
            item for item in candidate.inputs if item.snapshot_kind == "catalog"
        ]
        self.assertTrue(catalog_inputs)
        self.assertTrue(all(item.content_hash for item in catalog_inputs))
        for packet in candidate.writer_packets:
            packet_snapshots = [
                item for item in packet.inputs if item.input_type == "compile-snapshot"
            ]
            self.assertEqual(packet_snapshots, compile_snapshots)
            payload = packet.to_dict()["payload"]
            self.assertEqual(
                set(payload["section_plan"]),
                {"id", "path", "content_hash", "semantic_hash"},
            )
            self.assertEqual(
                set(payload["evidence"]),
                {
                    "claims",
                    "results",
                    "sources",
                    "figures",
                    "gates",
                    "results_hierarchy",
                },
            )
            self.assertEqual(
                payload["citation_registry"],
                global_context["citation_registry"],
            )
            self.assertEqual(
                payload["evidence"]["results"][0]["quantity_contracts"][0]["id"],
                "QTY-0001",
            )
            self.assertEqual(
                payload["evidence"]["figures"][0]["figure_ref"],
                "figure:main-1",
            )

        serialized = json.dumps(candidate.to_dict(), ensure_ascii=False, sort_keys=True)
        self.assertNotIn(str(self.project), serialized)
        self.assertNotIn("% block:", serialized)
        self.assertNotIn("@article{", serialized)
        self.assertEqual(tracked_tree_snapshot(self.project), before)

        bundle = candidate.to_bundle()
        self.assertEqual(bundle.global_context, candidate.global_context)
        self.assertEqual(bundle.compile_id, candidate.compile_id)

    def test_materialized_documents_validate_against_closed_generated_schemas(
        self,
    ) -> None:
        candidate = materialize_compile(
            self.loaded,
            self.contracts,
            self.manuscript,
            self.request,
        )
        self.assertTrue(candidate.successful, candidate.findings)
        schema_root = ROOT / "template/_paperops/defaults/schemas"
        documents = {
            "compile-bundle": [candidate.to_bundle().to_dict()],
            "section-plan": [
                plan.to_dict() for plan in candidate.section_plans
            ],
            "writer-packet": [
                packet.to_dict() for packet in candidate.writer_packets
            ],
        }
        for name, values in documents.items():
            schema = load_schema_document(schema_root / f"{name}.schema.json")
            for index, value in enumerate(values):
                with self.subTest(schema=name, index=index):
                    self.assertEqual(validate_schema(value, schema), [])

    def test_approval_only_change_propagates_through_content_snapshot_and_packets(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changed_project = approved_project(
                Path(tmp),
                approval_note="Same approval decision with a changed audit note.",
            )
            changed_loaded = load_compile_inputs(changed_project, self.request)
            changed_contracts = CompileContractSnapshot.from_contracts(
                resolve_section_contract(changed_project, kind)
                for kind in ("methods", "results", "discussion")
            )
            changed_manuscript = scan_manuscript(changed_project)

            baseline_claim = next(
                item for item in self.loaded.objects if item.object_id == "CLM-0001"
            )
            changed_claim = next(
                item for item in changed_loaded.objects if item.object_id == "CLM-0001"
            )
            self.assertEqual(
                baseline_claim.semantic_hash,
                changed_claim.semantic_hash,
            )
            self.assertNotEqual(
                baseline_claim.content_hash,
                changed_claim.content_hash,
            )
            self.assertNotEqual(
                self.loaded.snapshot_hash,
                changed_loaded.snapshot_hash,
            )

            baseline = materialize_compile(
                self.loaded,
                self.contracts,
                self.manuscript,
                self.request,
            )
            changed = materialize_compile(
                changed_loaded,
                changed_contracts,
                changed_manuscript,
                self.request,
            )
            self.assertTrue(baseline.successful, baseline.findings)
            self.assertTrue(changed.successful, changed.findings)
            self.assertNotEqual(baseline.compile_id, changed.compile_id)

            for candidate, loaded in (
                (baseline, self.loaded),
                (changed, changed_loaded),
            ):
                compile_snapshot = [
                    item
                    for item in candidate.inputs
                    if item.input_type == "compile-snapshot"
                ]
                self.assertEqual(len(compile_snapshot), 1)
                self.assertEqual(
                    compile_snapshot[0].content_hash,
                    loaded.snapshot_hash,
                )
                self.assertTrue(
                    all(
                        packet.inputs.count(compile_snapshot[0]) == 1
                        for packet in candidate.writer_packets
                    )
                )
            self.assertNotEqual(
                [packet.dependency_hash for packet in baseline.writer_packets],
                [packet.dependency_hash for packet in changed.writer_packets],
            )

    def test_typed_story_seed_rejects_wrong_type_before_projection(self) -> None:
        mutated = tuple(
            replace(item, object_type="move") if item.object_id == "STY-0001" else item
            for item in self.loaded.objects
        )

        candidate = materialize_compile(
            replace(self.loaded, objects=mutated),
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertFalse(candidate.successful)
        self.assertIn(
            "compile.dependency_type",
            [finding.code for finding in candidate.findings],
        )

    def test_declared_only_dependency_is_traversed_into_packet_coverage(self) -> None:
        extra = LoadedCatalogObject(
            object_id="SRC-9999",
            object_type="source",
            model_name="research",
            identity="_paperops/model/research/sources/SRC-9999.yml",
            revision=1,
            semantic_hash=HASH_B,
            content_hash=HASH_B,
            document={"id": "SRC-9999", "dependencies": []},
        )
        objects: list[LoadedCatalogObject] = []
        for item in self.loaded.objects:
            if item.object_id != "RES-0001":
                objects.append(item)
                continue
            document = _json_compatible(item.document)
            document["dependencies"] = [
                {
                    "target_id": "SRC-9999",
                    "relation": "provenance",
                    "expected_revision": 1,
                    "expected_hash": HASH_B,
                }
            ]
            objects.append(
                replace(
                    item,
                    document=document,
                )
            )
        objects.append(extra)

        candidate = materialize_compile(
            replace(self.loaded, objects=tuple(objects)),
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        self.assertIn("SRC-9999", {item.identity.rsplit("/", 1)[-1].removesuffix(".yml") for item in candidate.inputs})

    def test_rejected_story_context_is_not_promoted_to_authoring_evidence(self) -> None:
        baseline_claim = next(
            item for item in self.loaded.objects if item.object_id == "CLM-0001"
        )
        baseline_gate = next(
            item for item in self.loaded.objects if item.object_id == "GATE-0001"
        )
        rejected_claim_document = _json_compatible(baseline_claim.document)
        rejected_claim_document.update(
            {
                "id": "CLM-9999",
                "status": "proposed",
                "gate_id": "GATE-9999",
                "gate_status": "draft",
                "approvals": [],
                "statement": "REJECTED STORY CLAIM MUST NOT REACH A WRITER.",
            }
        )
        rejected_gate_document = _json_compatible(baseline_gate.document)
        rejected_gate_document.update(
            {
                "id": "GATE-9999",
                "claim_id": "CLM-9999",
                "gate_decision": "draft",
                "analysis_request_refs": [],
            }
        )
        extra_objects = (
            LoadedCatalogObject(
                object_id="CLM-9999",
                object_type="claim",
                model_name="research",
                identity="_paperops/model/research/claims/CLM-9999.yml",
                revision=1,
                semantic_hash=model_semantic_hash(
                    rejected_claim_document,
                    excluded_paths=HASH_EXCLUSIONS,
                ),
                content_hash=model_semantic_hash(rejected_claim_document),
                document=rejected_claim_document,
            ),
            LoadedCatalogObject(
                object_id="GATE-9999",
                object_type="scientific_gate",
                model_name="research",
                identity="_paperops/model/research/gates/GATE-9999.yml",
                revision=1,
                semantic_hash=model_semantic_hash(
                    rejected_gate_document,
                    excluded_paths=HASH_EXCLUSIONS,
                ),
                content_hash=model_semantic_hash(rejected_gate_document),
                document=rejected_gate_document,
            ),
        )
        objects: list[LoadedCatalogObject] = []
        for item in self.loaded.objects:
            if item.object_id != "MOV-0004":
                objects.append(item)
                continue
            document = _json_compatible(item.document)
            document["claim_ids"] = ["CLM-9999"]
            objects.append(
                replace(
                    item,
                    document=document,
                    semantic_hash=model_semantic_hash(document),
                    content_hash=model_semantic_hash(document),
                )
            )
        objects.extend(extra_objects)

        documents = []
        for item in self.loaded.documents:
            if item.model_name != "editorial" or item.document_type != "aggregate":
                documents.append(item)
                continue
            document = _json_compatible(item.document)
            document["claim_roles"]["cut"] = {
                "claim_ids": ["CLM-9999"],
                "none_reason": "",
            }
            next(
                move
                for move in document["argument_moves"]
                if move["id"] == "MOV-0004"
            )["claim_ids"] = ["CLM-9999"]
            documents.append(
                replace(
                    item,
                    document=document,
                    semantic_hash=model_semantic_hash(document),
                    content_hash=model_semantic_hash(document),
                )
            )

        candidate = materialize_compile(
            replace(
                self.loaded,
                objects=tuple(objects),
                documents=tuple(documents),
                snapshot_hash=HASH_B,
            ),
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        self.assertIn(
            "CLM-9999",
            {item.identity.rsplit("/", 1)[-1].removesuffix(".yml") for item in candidate.inputs},
        )
        self.assertEqual(
            candidate.to_dict()["global_context"]["claim_roles"]["cut"][
                "claim_ids"
            ],
            ["CLM-9999"],
        )
        authoring_material = json.dumps(
            {
                "projections": [
                    plan.to_dict()["projection"]
                    for plan in candidate.section_plans
                ],
                "payloads": [
                    packet.to_dict()["payload"]
                    for packet in candidate.writer_packets
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn("CLM-9999", authoring_material)
        self.assertNotIn(
            "REJECTED STORY CLAIM MUST NOT REACH A WRITER",
            authoring_material,
        )

    def test_privacy_scans_actual_global_projection_without_echoing_value(self) -> None:
        documents = []
        private_value = "Use /private/author-only/result.h5 for the reader arc."
        for item in self.loaded.documents:
            if item.model_name != "editorial" or item.document_type != "aggregate":
                documents.append(item)
                continue
            document = _json_compatible(item.document)
            document["reader_transformation"] = {
                "from": private_value,
                "to": "A bounded public conclusion.",
            }
            documents.append(
                replace(
                    item,
                    document=document,
                    semantic_hash=model_semantic_hash(document),
                    content_hash=model_semantic_hash(document),
                )
            )
        candidate = self.assert_blocked_with(
            "compile.privacy_private_material",
            loaded=replace(
                self.loaded,
                documents=tuple(documents),
                snapshot_hash=HASH_B,
            ),
        )
        self.assertNotIn(
            private_value,
            json.dumps(candidate.to_dict(), ensure_ascii=False),
        )

    def test_private_nonprojected_approval_note_does_not_enter_writer_material(
        self,
    ) -> None:
        private_note = "Audit evidence remains at /private/reviewer/approval.txt."

        def change_note(document):
            document["approvals"][0]["note"] = private_note

        loaded = mutated_loaded_object(self.loaded, "CLM-0001", change_note)
        baseline_claim = next(
            item for item in self.loaded.objects if item.object_id == "CLM-0001"
        )
        changed_claim = next(
            item for item in loaded.objects if item.object_id == "CLM-0001"
        )
        self.assertEqual(baseline_claim.semantic_hash, changed_claim.semantic_hash)
        self.assertNotEqual(baseline_claim.content_hash, changed_claim.content_hash)

        candidate = materialize_compile(
            loaded,
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        self.assertNotIn(
            private_note,
            json.dumps(candidate.to_dict(), ensure_ascii=False),
        )

    def test_analysis_request_identity_has_dedicated_snapshot_type(self) -> None:
        self.assertEqual(
            _input_type(
                "_paperops/requests/analysis/AREQ-0001.md",
                frozenset(),
            ),
            "analysis-request",
        )

    def assert_blocked_with(
        self,
        code: str,
        *,
        loaded=None,
        contracts=None,
        manuscript=None,
        request=None,
    ) -> CompileBundleCandidate:
        candidate = materialize_compile(
            loaded or self.loaded,
            contracts or self.contracts,
            manuscript or self.manuscript,
            request or self.request,
        )
        self.assertFalse(candidate.successful)
        self.assertEqual(candidate.section_plans, ())
        self.assertEqual(candidate.writer_packets, ())
        self.assertIn(code, [finding.code for finding in candidate.findings])
        return candidate

    def test_section_approval_missing_rejected_and_stale_are_distinct(self) -> None:
        def without_approval(document):
            document["approvals"] = []

        def rejected(document):
            document["approvals"][0]["decision"] = "rejected"

        def stale(document):
            document["approvals"][0]["object_hash"] = HASH_B

        for mutation, code in (
            (without_approval, "compile.plan_approval_missing"),
            (rejected, "compile.plan_approval_rejected"),
            (stale, "compile.plan_approval_stale"),
        ):
            with self.subTest(code=code):
                self.assert_blocked_with(
                    code,
                    loaded=mutated_loaded_object(
                        self.loaded,
                        "SEC-0002",
                        mutation,
                    ),
                )

    def test_research_approval_and_gate_readiness_are_revalidated(self) -> None:
        self.assert_blocked_with(
            "compile.research_approval_missing",
            loaded=mutated_loaded_object(
                self.loaded,
                "CLM-0001",
                lambda document: document.update({"approvals": []}),
            ),
        )
        self.assert_blocked_with(
            "compile.research_gate",
            loaded=mutated_loaded_object(
                self.loaded,
                "GATE-0001",
                lambda document: document.update({"gate_decision": "draft"}),
            ),
        )

    def test_missing_wrong_type_stale_and_uncovered_dependencies_are_distinct(
        self,
    ) -> None:
        self.assert_blocked_with(
            "compile.dependency_missing",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document["claim_refs"].__setitem__(0, "CLM-9999"),
            ),
        )
        self.assert_blocked_with(
            "compile.dependency_type",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document["claim_refs"].__setitem__(0, "RES-0001"),
            ),
        )
        self.assert_blocked_with(
            "compile.dependency_stale",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document["dependencies"][0].update(
                    {"expected_hash": HASH_B}
                ),
            ),
        )
        self.assert_blocked_with(
            "compile.dependency_uncovered",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document.update(
                    {
                        "dependencies": [
                            dependency
                            for dependency in document["dependencies"]
                            if dependency["target_id"] != "CLM-0001"
                        ]
                    }
                ),
            ),
        )

    def test_move_primary_contract_marker_and_scope_are_blocking(self) -> None:
        self.assert_blocked_with(
            "compile.move_primary",
            loaded=mutated_loaded_object(
                self.loaded,
                "SEC-0002",
                lambda document: document["move_bindings"][1].update(
                    {"role": "echo"}
                ),
            ),
        )
        bad_contract = replace(
            self.contracts.contracts["results"],
            findings=(
                CompileFinding(
                    code="compile.contract_invalid",
                    pointer="/results",
                    message="contract is invalid",
                ),
            ),
        )
        self.assert_blocked_with(
            "compile.contract_invalid",
            contracts=CompileContractSnapshot.from_contracts(
                [
                    self.contracts.contracts["methods"],
                    bad_contract,
                    self.contracts.contracts["discussion"],
                ]
            ),
        )
        self.assert_blocked_with(
            "compile.tex_binding_missing",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document.update(
                    {"ja_tex_block_id": "results.missing.01"}
                ),
            ),
        )
        bad_scope = replace(
            self.request,
            write_scope=replace(
                self.request.write_scope,
                files=self.request.write_scope.files[:-1],
            ),
        )
        self.assert_blocked_with("compile.scope_files", request=bad_scope)

    def test_private_writer_projection_is_rejected_without_echo(self) -> None:
        private = "/private/reviewer/raw-result.h5"
        candidate = self.assert_blocked_with(
            "compile.privacy_private_material",
            loaded=mutated_loaded_object(
                self.loaded,
                "CLM-0001",
                lambda document: document.update({"statement": private}),
            ),
        )
        self.assertNotIn(private, json.dumps(candidate.to_dict(), ensure_ascii=False))

    def test_block_scope_keeps_global_topology_but_never_widens_write_targets(
        self,
    ) -> None:
        base_block = next(
            item for item in self.loaded.objects if item.object_id == "BLK-0002"
        )
        block_document = _json_compatible(base_block.document)
        block_document.update(
            {
                "id": "BLK-0004",
                "position": 2,
                "ja_tex_block_id": "results.refs.01",
                "en_tex_block_id": "results.refs.01",
            }
        )
        extra_block = replace(
            base_block,
            object_id="BLK-0004",
            identity="_paperops/model/manuscript/blocks/BLK-0004.yml",
            semantic_hash=model_semantic_hash(
                block_document,
                excluded_paths=HASH_EXCLUSIONS,
            ),
            content_hash=model_semantic_hash(block_document),
            document=block_document,
        )

        def add_planned_block(document):
            document["ordered_block_ids"].append("BLK-0004")
            document["approvals"] = []
            current = model_semantic_hash(document, excluded_paths=HASH_EXCLUSIONS)
            document["approvals"] = [
                {
                    "approval_id": "APR-0001",
                    "kind": "editorial_choice",
                    "decision": "approved",
                    "object_revision": 1,
                    "object_hash": current,
                    "actor": "human",
                    "note": "Approved two-block topology.",
                }
            ]

        loaded = mutated_loaded_object(self.loaded, "SEC-0002", add_planned_block)
        loaded = replace(loaded, objects=(*loaded.objects, extra_block))
        request = CompileRequest(
            targets=("SEC-0002",),
            write_scope=WriteScope(
                level="block",
                languages=("ja", "en"),
                files=(
                    "manuscript/ja/sections/30_results.tex",
                    "manuscript/en/sections/30_results.tex",
                ),
                section_ids=("SEC-0002",),
                block_ids=("BLK-0002",),
                allowed_operations=("rewrite",),
            ),
        )
        contracts = CompileContractSnapshot.from_contracts(
            [self.contracts.contracts["results"]]
        )

        candidate = materialize_compile(
            loaded,
            contracts,
            self.manuscript,
            request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        self.assertEqual(
            candidate.section_plans[0].ordered_block_ids,
            ("BLK-0002", "BLK-0004"),
        )
        self.assertEqual(candidate.writer_packets[0].write_scope.block_ids, ("BLK-0002",))
        self.assertEqual(
            [row["section_id"] for row in candidate.to_dict()["global_context"]["section_block_map"]],
            ["SEC-0001", "SEC-0002", "SEC-0003"],
        )
        self.assertEqual(
            candidate.section_plans[0].to_dict()["projection"]["connections"],
            {"previous_section_id": "SEC-0001", "next_section_id": "SEC-0003"},
        )
        section_rows = candidate.to_dict()["global_context"]["section_block_map"]
        self.assertTrue(all(row["blocks"] for row in section_rows))
        self.assertEqual(
            {
                item.identity
                for item in candidate.inputs
                if item.input_type == "block"
            },
            {
                "_paperops/model/manuscript/blocks/BLK-0001.yml",
                "_paperops/model/manuscript/blocks/BLK-0002.yml",
                "_paperops/model/manuscript/blocks/BLK-0003.yml",
                "_paperops/model/manuscript/blocks/BLK-0004.yml",
            },
        )

    def test_global_topology_preserves_manuscript_index_order(self) -> None:
        documents = []
        for item in self.loaded.documents:
            if item.model_name != "manuscript" or item.document_type != "index":
                documents.append(item)
                continue
            document = _json_compatible(item.document)
            records = document["records"]
            sections = {
                row["id"]: row
                for row in records
                if row["record_type"] == "section"
            }
            blocks = [row for row in records if row["record_type"] == "block"]
            document["records"] = [
                sections["SEC-0003"],
                sections["SEC-0001"],
                sections["SEC-0002"],
                *blocks,
            ]
            documents.append(
                replace(
                    item,
                    document=document,
                    semantic_hash=model_semantic_hash(document),
                    content_hash=model_semantic_hash(document),
                )
            )

        candidate = materialize_compile(
            replace(
                self.loaded,
                documents=tuple(documents),
                snapshot_hash=HASH_B,
            ),
            self.contracts,
            self.manuscript,
            self.request,
        )

        self.assertTrue(candidate.successful, candidate.findings)
        rows = candidate.to_dict()["global_context"]["section_block_map"]
        self.assertEqual(
            [row["section_id"] for row in rows],
            ["SEC-0003", "SEC-0001", "SEC-0002"],
        )
        middle = next(row for row in rows if row["section_id"] == "SEC-0001")
        self.assertEqual(middle["previous_section_id"], "SEC-0003")
        self.assertEqual(middle["next_section_id"], "SEC-0002")
        self.assertEqual(
            candidate.section_plans[0].to_dict()["projection"]["connections"],
            {"previous_section_id": "SEC-0003", "next_section_id": "SEC-0002"},
        )

    def test_section_kind_revision_and_block_parent_are_never_synthesized(self) -> None:
        without_revision = replace(
            self.loaded,
            objects=tuple(
                replace(item, revision=None)
                if item.object_id == "SEC-0002"
                else item
                for item in self.loaded.objects
            ),
            snapshot_hash=HASH_B,
        )
        self.assert_blocked_with(
            "compile.section_revision",
            loaded=without_revision,
        )

        self.assert_blocked_with(
            "compile.section_kind",
            loaded=mutated_loaded_object(
                self.loaded,
                "SEC-0002",
                lambda document: document.__setitem__(
                    "section_kind",
                    "unsupported-kind",
                ),
            ),
        )

        self.assert_blocked_with(
            "compile.scope_topology",
            loaded=mutated_loaded_object(
                self.loaded,
                "BLK-0002",
                lambda document: document.__setitem__(
                    "section_id",
                    "SEC-0001",
                ),
            ),
        )

    def test_section_contract_ref_must_bind_the_resolved_section_kind(self) -> None:
        def wrong_contract(document):
            document["contract_refs"] = ["contract:discussion"]
            document["approvals"] = []
            current = model_semantic_hash(document, excluded_paths=HASH_EXCLUSIONS)
            document["approvals"] = [
                {
                    "approval_id": "APR-0001",
                    "kind": "editorial_choice",
                    "decision": "approved",
                    "object_revision": 1,
                    "object_hash": current,
                    "actor": "human",
                    "note": "Approved.",
                }
            ]

        self.assert_blocked_with(
            "compile.contract_binding",
            loaded=mutated_loaded_object(
                self.loaded,
                "SEC-0002",
                wrong_contract,
            ),
        )

    def test_predicted_material_requires_markers_and_open_snapshotted_areq(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = approved_project(
                Path(tmp),
                analysis_request_refs=("AREQ-0001",),
            )
            (project / "_paperops/requests/analysis/AREQ-0001.md").unlink()
            marker_lines = (
                "% PREDICTED-RESULT: bounded expectation AREQ-0001\n"
                "% SIM-REQUEST: AREQ-0001\n"
                "% EXPECTATION-BASIS: approved model boundary AREQ-0001\n"
                "% REPLACE-XX: AREQ-0001\n"
            )
            for language in ("ja", "en"):
                path = project / f"manuscript/{language}/sections/30_results.tex"
                text = path.read_text(encoding="utf-8")
                path.write_text(
                    text.replace(
                        "% block: results.traceability.01\n",
                        "% block: results.traceability.01\n" + marker_lines,
                    ),
                    encoding="utf-8",
                )

            missing_request = scan_manuscript(project)
            self.assert_blocked_with(
                "compile.prediction_areq",
                loaded=load_compile_inputs(project, self.request),
                manuscript=missing_request,
            )

            request_path = project / "_paperops/requests/analysis/AREQ-0001.md"
            request_path.write_text(
                "---\ntype: analysis_request\nid: AREQ-0001\nstatus: planned\n---\n\n"
                "RAW REQUEST BODY MUST NOT ENTER THE PACKET.\n",
                encoding="utf-8",
            )
            open_request = scan_manuscript(project)

            candidate = materialize_compile(
                load_compile_inputs(project, self.request),
                self.contracts,
                open_request,
                self.request,
            )

            self.assertTrue(candidate.successful, candidate.findings)
            packet = next(
                packet
                for packet in candidate.writer_packets
                if packet.write_scope.section_ids == ("SEC-0002",)
            )
            self.assertEqual(
                packet.to_dict()["payload"]["predicted_result"],
                {
                    "enabled": True,
                    "analysis_request_ids": ["AREQ-0001"],
                    "analysis_requests": [open_request.analysis_requests[0].to_dict()],
                },
            )
            request_inputs = [
                item
                for item in packet.inputs
                if item.input_type == "analysis-request"
            ]
            self.assertEqual(len(request_inputs), 1)
            self.assertEqual(request_inputs[0].relation, "prediction-authority")
            self.assertEqual(
                request_inputs[0].content_hash,
                open_request.analysis_requests[0].content_hash,
            )
            self.assertNotIn(
                "RAW REQUEST BODY MUST NOT ENTER THE PACKET",
                json.dumps(candidate.to_dict(), ensure_ascii=False),
            )
            for observed_packet in (
                item
                for item in candidate.writer_packets
                if item.write_scope.section_ids != ("SEC-0002",)
            ):
                self.assertEqual(
                    observed_packet.to_dict()["payload"]["predicted_result"],
                    {
                        "enabled": False,
                        "analysis_request_ids": [],
                        "analysis_requests": [],
                    },
                )
                self.assertFalse(
                    any(
                        item.input_type == "analysis-request"
                        for item in observed_packet.inputs
                    )
                )
                self.assertFalse(
                    any(
                        item["identity"] == open_request.analysis_requests[0].identity
                        for item in observed_packet.to_dict()["read_context"][
                            "manuscript_files"
                        ]
                    )
                )

            request_path.write_text(
                "---\ntype: analysis_request\nid: AREQ-0001\nstatus: reconciled\n---\n",
                encoding="utf-8",
            )
            self.assert_blocked_with(
                "compile.prediction_areq_status",
                loaded=load_compile_inputs(project, self.request),
                manuscript=scan_manuscript(project),
            )

    def test_predicted_material_requires_the_complete_marker_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = approved_project(
                Path(tmp),
                analysis_request_refs=("AREQ-0001",),
            )
            for language in ("ja", "en"):
                path = project / f"manuscript/{language}/sections/30_results.tex"
                text = path.read_text(encoding="utf-8")
                path.write_text(
                    text.replace(
                        "% block: results.traceability.01\n",
                        "% block: results.traceability.01\n"
                        "% PREDICTED-RESULT: AREQ-0001\n",
                    ),
                    encoding="utf-8",
                )
            request_path = project / "_paperops/requests/analysis/AREQ-0001.md"
            request_path.write_text(
                "---\ntype: analysis_request\nid: AREQ-0001\nstatus: planned\n---\n",
                encoding="utf-8",
            )

            self.assert_blocked_with(
                "compile.prediction_markers",
                loaded=load_compile_inputs(project, self.request),
                manuscript=scan_manuscript(project),
            )

            for language in ("ja", "en"):
                path = project / f"manuscript/{language}/sections/30_results.tex"
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        "% PREDICTED-RESULT: AREQ-0001\n",
                        "% PREDICTED-RESULT: bounded expectation\n"
                        "% SIM-REQUEST: pending analysis\n"
                        "% EXPECTATION-BASIS: approved boundary\n"
                        "% REPLACE-XX: pending replacement\n"
                        "Related request AREQ-0001 is mentioned outside the markers.\n",
                    ),
                    encoding="utf-8",
                )
            self.assert_blocked_with(
                "compile.prediction_areq",
                loaded=load_compile_inputs(project, self.request),
                manuscript=scan_manuscript(project),
            )

    def test_predicted_material_requires_gate_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = approved_project(Path(tmp))
            marker_lines = (
                "% PREDICTED-RESULT: bounded expectation AREQ-0001\n"
                "% SIM-REQUEST: AREQ-0001\n"
                "% EXPECTATION-BASIS: approved model boundary AREQ-0001\n"
                "% REPLACE-XX: AREQ-0001\n"
            )
            for language in ("ja", "en"):
                path = project / f"manuscript/{language}/sections/30_results.tex"
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        "% block: results.traceability.01\n",
                        "% block: results.traceability.01\n" + marker_lines,
                    ),
                    encoding="utf-8",
                )
            (project / "_paperops/requests/analysis/AREQ-0001.md").write_text(
                "---\ntype: analysis_request\nid: AREQ-0001\nstatus: planned\n---\n",
                encoding="utf-8",
            )
            self.assert_blocked_with(
                "compile.prediction_gate_link",
                loaded=load_compile_inputs(project, self.request),
                manuscript=scan_manuscript(project),
            )

    def test_predicted_markers_are_complete_and_consistent_per_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = approved_project(
                Path(tmp),
                analysis_request_refs=("AREQ-0001",),
            )
            complete = (
                "% PREDICTED-RESULT: AREQ-0001\n"
                "% SIM-REQUEST: AREQ-0001\n"
                "% EXPECTATION-BASIS: AREQ-0001\n"
                "% REPLACE-XX: AREQ-0001\n"
            )
            ja_path = project / "manuscript/ja/sections/30_results.tex"
            en_path = project / "manuscript/en/sections/30_results.tex"
            ja_path.write_text(
                ja_path.read_text(encoding="utf-8").replace(
                    "% block: results.traceability.01\n",
                    "% block: results.traceability.01\n" + complete,
                ),
                encoding="utf-8",
            )
            en_path.write_text(
                en_path.read_text(encoding="utf-8").replace(
                    "% block: results.traceability.01\n",
                    "% block: results.traceability.01\n"
                    "% PREDICTED-RESULT: AREQ-0002\n",
                ),
                encoding="utf-8",
            )
            for request_id in ("AREQ-0001", "AREQ-0002"):
                (project / f"_paperops/requests/analysis/{request_id}.md").write_text(
                    "---\ntype: analysis_request\n"
                    f"id: {request_id}\nstatus: planned\n---\n",
                    encoding="utf-8",
                )
            candidate = self.assert_blocked_with(
                "compile.prediction_markers",
                loaded=load_compile_inputs(project, self.request),
                manuscript=scan_manuscript(project),
            )
            self.assertIn(
                "compile.prediction_areq_mismatch",
                [finding.code for finding in candidate.findings],
            )

    def test_internal_query_defers_only_the_safe_areq_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = approved_project(
                Path(tmp),
                analysis_request_refs=("AREQ-0001",),
            )
            issue_index_path = project / "_paperops/model/issues/index.yml"
            issue_index = yaml.safe_load(
                issue_index_path.read_text(encoding="utf-8")
            )
            issue_index["records"] = [
                row
                for row in issue_index["records"]
                if row["id"] != "AREQ-0001"
            ]
            issue_index_path.write_text(
                yaml.safe_dump(issue_index, sort_keys=False),
                encoding="utf-8",
            )

            internal_arguments = (
                "--root",
                project,
                "--model",
                "research",
                "--phase",
                "all",
                "--json",
                "--print-hash",
                "--internal-compile-query",
            )
            deferred = run_python_script(CHECKER, *internal_arguments)
            normal = run_python_script(
                CHECKER,
                "--root",
                project,
                "--model",
                "research",
                "--phase",
                "references",
                "--json",
            )
            self.assertEqual(deferred.returncode, 0, deferred.stdout)
            self.assertNotEqual(normal.returncode, 0)
            normal_findings = json.loads(normal.stdout)["findings"]
            self.assertTrue(
                any(
                    item["code"] == "reference.dangling"
                    and "/analysis_request_refs/" in item["pointer"]
                    for item in normal_findings
                )
            )

            def set_route(route_ref: str) -> None:
                research_index_path = (
                    project / "_paperops/model/research/index.yml"
                )
                research_index = yaml.safe_load(
                    research_index_path.read_text(encoding="utf-8")
                )
                gate_row = next(
                    row
                    for row in research_index["records"]
                    if row["id"] == "GATE-0001"
                )
                gate_path = project / gate_row["document"]
                gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
                gate["external_validation_gates"] = [
                    {
                        "id": "EXT-0001",
                        "blocking_claim_ref": "CLM-0001",
                        "required_external_evidence": "A bounded external check.",
                        "allowed_wording": "Association within the checked regime.",
                        "must_not_claim": "Universal causality.",
                        "route_ref": route_ref,
                    }
                ]
                gate_hash = model_semantic_hash(
                    gate,
                    excluded_paths=HASH_EXCLUSIONS,
                )
                gate_row["expected_hash"] = gate_hash
                gate_path.write_text(
                    yaml.safe_dump(gate, sort_keys=False),
                    encoding="utf-8",
                )
                research_index_path.write_text(
                    yaml.safe_dump(research_index, sort_keys=False),
                    encoding="utf-8",
                )

                manuscript_index_path = (
                    project / "_paperops/model/manuscript/index.yml"
                )
                manuscript_index = yaml.safe_load(
                    manuscript_index_path.read_text(encoding="utf-8")
                )
                for row in manuscript_index["records"]:
                    if row["record_type"] != "section":
                        continue
                    section_path = project / row["document"]
                    section = yaml.safe_load(
                        section_path.read_text(encoding="utf-8")
                    )
                    for dependency in section["dependencies"]:
                        if dependency["target_id"] == "GATE-0001":
                            dependency["expected_hash"] = gate_hash
                    section_hash = model_semantic_hash(
                        section,
                        excluded_paths=HASH_EXCLUSIONS,
                    )
                    for approval in section["approvals"]:
                        if approval["kind"] == "editorial_choice":
                            approval["object_hash"] = section_hash
                    row["expected_hash"] = section_hash
                    section_path.write_text(
                        yaml.safe_dump(section, sort_keys=False),
                        encoding="utf-8",
                    )
                manuscript_index_path.write_text(
                    yaml.safe_dump(manuscript_index, sort_keys=False),
                    encoding="utf-8",
                )

            set_route("CLM-0001")
            wrong_type = run_python_script(CHECKER, *internal_arguments)
            self.assertNotEqual(wrong_type.returncode, 0)
            self.assertTrue(
                any(
                    item["code"] == "reference.type"
                    and item["pointer"].endswith("/route_ref")
                    for item in json.loads(wrong_type.stdout)["findings"]
                )
            )

            set_route("AREQ-9999")
            other_dangling = run_python_script(CHECKER, *internal_arguments)
            self.assertNotEqual(other_dangling.returncode, 0)
            self.assertTrue(
                any(
                    item["code"] == "reference.dangling"
                    and item["pointer"].endswith("/route_ref")
                    for item in json.loads(other_dangling.stdout)["findings"]
                )
            )


class P3CompileMaterializeTypeTest(unittest.TestCase):
    def test_input_snapshot_keeps_legacy_shape_and_optionally_records_content_hash(
        self,
    ) -> None:
        legacy = InputSnapshot(
            identity="_paperops/model/research/claims/CLM-0001.yml",
            input_type="claim",
            semantic_hash=HASH_A,
            relation="supports",
            model_name="research",
            revision=1,
        )
        self.assertNotIn("content_hash", legacy.to_dict())

        complete = InputSnapshot(
            identity="_paperops/model/research/claims/CLM-0001.yml",
            input_type="claim",
            semantic_hash=HASH_A,
            relation="supports",
            model_name="research",
            revision=1,
            content_hash=HASH_B,
        )
        self.assertEqual(complete.to_dict()["hash"], HASH_A)
        self.assertEqual(complete.to_dict()["content_hash"], HASH_B)
        with self.assertRaises(ValueError):
            InputSnapshot(
                identity="_paperops/model/research/claims/CLM-0001.yml",
                input_type="claim",
                semantic_hash=HASH_A,
                relation="supports",
                content_hash="not-a-hash",
            )

    def test_contract_snapshot_is_sorted_immutable_and_hashes_all_target_kinds(
        self,
    ) -> None:
        contracts = [
            resolve_section_contract(ROOT / "template", kind)
            for kind in ("results", "methods", "discussion")
        ]

        snapshot = CompileContractSnapshot.from_contracts(reversed(contracts))

        self.assertEqual(
            tuple(snapshot.contracts),
            ("discussion", "methods", "results"),
        )
        self.assertRegex(snapshot.snapshot_hash, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            snapshot,
            CompileContractSnapshot.from_contracts(contracts),
        )
        with self.assertRaises(TypeError):
            snapshot.contracts["results"] = contracts[0]  # type: ignore[index]

    def test_public_materializer_surface_is_explicit(self) -> None:
        self.assertTrue(callable(materialize_compile))
        self.assertFalse(issubclass(CompileBundleCandidate, CompileBundle))

    def test_failed_candidate_has_no_success_products_and_cannot_become_bundle(
        self,
    ) -> None:
        request = CompileRequest(
            targets=(),
            write_scope=WriteScope(
                level="manuscript",
                languages=("ja", "en"),
                files=(),
            ),
        )
        finding = CompileFinding(
            code="compile.example",
            pointer="/inputs",
            message="stable public diagnostic",
        )
        candidate = CompileBundleCandidate(
            compiler_contract_version="p3-typed-compile-v1",
            compile_id="compile-v1-" + "c" * 64,
            status="blocked",
            source_mode="authoritative",
            applicable=True,
            request=request,
            authority=(),
            inputs=(),
            global_context={},
            section_plans=(),
            writer_packets=(),
            findings=(finding,),
        )

        self.assertEqual(candidate.section_plans, ())
        self.assertEqual(candidate.writer_packets, ())
        self.assertFalse(candidate.successful)
        with self.assertRaises(ValueError):
            candidate.to_bundle()

    def test_candidate_applicability_tracks_source_and_empty_ready_cannot_convert(
        self,
    ) -> None:
        request = CompileRequest(
            targets=(),
            write_scope=WriteScope(
                level="manuscript",
                languages=("ja", "en"),
                files=(),
            ),
            source_mode="shadow",
            shadow_transaction_id="model-20260712T000000000000Z-aaaaaaaaaaaa",
        )
        global_context = {
            "schema_version": 1,
            "selected_story": {"id": "STY-0001"},
            "extensions": {},
        }
        candidate = CompileBundleCandidate(
            compiler_contract_version="p3-typed-compile-v1",
            compile_id="compile-v1-" + "d" * 64,
            status="ready",
            source_mode="shadow",
            applicable=False,
            request=request,
            authority=(),
            inputs=(),
            global_context=global_context,
            section_plans=(),
            writer_packets=(),
            findings=(),
        )

        self.assertFalse(candidate.successful)
        with self.assertRaises(ValueError):
            candidate.to_bundle()

        with self.assertRaises(ValueError):
            CompileBundleCandidate(
                compiler_contract_version="p3-typed-compile-v1",
                compile_id="compile-v1-" + "e" * 64,
                status="ready",
                source_mode="authoritative",
                applicable=False,
                request=CompileRequest(
                    targets=(),
                    write_scope=WriteScope(
                        level="manuscript",
                        languages=("ja", "en"),
                        files=(),
                    ),
                ),
                authority=(),
                inputs=(),
                global_context={},
                section_plans=(),
                writer_packets=(),
                findings=(),
            )


if __name__ == "__main__":
    unittest.main()
