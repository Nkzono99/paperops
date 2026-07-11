from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from tests.test_issue_model import (
    analysis_request,
    feedback,
    response,
    review_round,
    writing_request,
)
from tests.test_manuscript_model import block, section
from tests.test_publication_model import publication
from tests.test_research_model import claim, figure, gate, result, source

from paperops_models import dependency_hash, build_object_catalog, load_model_document
from paperops_schema import load_document, load_registry, semantic_hash


HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")
MODEL_DIRECTORIES = {"research": "research", "manuscript": "manuscript", "issue": "issues"}
RECORD_DIRECTORIES = {
    "claim": "claims",
    "result": "results",
    "figure": "figures",
    "source": "sources",
    "scientific_gate": "gates",
    "section": "sections",
    "block": "blocks",
    "feedback": "feedback",
    "analysis_request": "analysis",
    "writing_request": "writing",
    "response": "responses",
    "review_round": "rounds",
}


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _record_path(model_name: str, document: dict) -> str:
    return (
        f"_paperops/model/{MODEL_DIRECTORIES[model_name]}/"
        f"{RECORD_DIRECTORIES[str(document['record_type'])]}/{document['id']}.yml"
    )


def _write_index(project: Path, model_name: str, documents: list[dict]) -> None:
    records = []
    for document in documents:
        relative = _record_path(model_name, document)
        _write_json(project / relative, document)
        records.append(
            {
                "id": document["id"],
                "record_type": document["record_type"],
                "document": relative,
                "expected_revision": document["revision"],
                "expected_hash": semantic_hash(
                    document, excluded_paths=HASH_EXCLUSIONS
                ),
            }
        )
    index = {
        "model_name": model_name,
        "schema_version": 1,
        "index_revision": 1,
        "records": records,
        "extensions": {},
        "metadata": {"updated_at": "2026-07-11"},
    }
    directory = MODEL_DIRECTORIES[model_name]
    _write_json(project / f"_paperops/model/{directory}/index.yml", index)


def reindex_model(project: Path, model_name: str) -> None:
    directory = MODEL_DIRECTORIES[model_name]
    index_path = project / f"_paperops/model/{directory}/index.yml"
    index = load_document(index_path)
    for row in index["records"]:
        document = load_document(project / row["document"])
        row["expected_revision"] = document["revision"]
        row["expected_hash"] = semantic_hash(
            document, excluded_paths=HASH_EXCLUSIONS
        )
    _write_json(index_path, index)


def _research_documents(visual_id: str) -> list[dict]:
    foreground = claim()
    foreground["visual_obligation_refs"] = [visual_id]
    foreground_hash = semantic_hash(foreground, excluded_paths=HASH_EXCLUSIONS)
    foreground["approvals"] = [
        {
            "approval_id": "APR-1001",
            "kind": "scientific_scope",
            "decision": "approved",
            "object_revision": 1,
            "object_hash": foreground_hash,
            "actor": "human",
            "note": "Synthetic fixture scope approved.",
        }
    ]

    foreground_gate = gate()
    claims = [foreground]
    gates = [foreground_gate]
    for number in range(2, 5):
        claim_document = copy.deepcopy(foreground)
        claim_document.update(
            {
                "id": f"CLM-{number:04d}",
                "status": "proposed",
                "figure_refs": [],
                "visual_obligation_refs": [],
                "no_figure_reason": "This synthetic supporting claim has no figure obligation.",
                "assumptions": [f"ASM-{number:04d}"],
                "gate_id": f"GATE-{number:04d}",
                "gate_status": "draft",
                "human_approval": "needed",
                "abstract_conclusion_allowed": False,
                "approvals": [],
            }
        )
        claims.append(claim_document)
        gate_document = copy.deepcopy(foreground_gate)
        gate_document.update(
            {
                "id": f"GATE-{number:04d}",
                "status": "draft",
                "claim_id": f"CLM-{number:04d}",
                "gate_decision": "draft",
                "approved_writing_scope": "",
                "block_reason": "Synthetic supporting claim remains proposed.",
                "human_approval": "needed",
            }
        )
        gate_document["central_assumptions"][0].update(
            {
                "id": f"ASM-{number:04d}",
                "guarded_claim_refs": [f"CLM-{number:04d}"],
            }
        )
        gate_document["claim_stress_tests"][0]["id"] = f"STRESS-{number:04d}"
        gate_document["external_validation_gates"][0].update(
            {
                "id": f"EXT-{number:04d}",
                "blocking_claim_ref": f"CLM-{number:04d}",
            }
        )
        gate_document["history"] = [
            {
                "event_id": f"HIS-{number:04d}",
                "decision": "draft",
                "note": "Synthetic draft gate.",
            }
        ]
        gates.append(gate_document)
    figure_document = figure()
    figure_document["visual_obligation_refs"] = [visual_id]
    return [*claims, result(), figure_document, source(), *gates]


def materialize_p1b_fixture(project: Path, case_dir: Path) -> None:
    editorial_dir = project / "_paperops/model/editorial"
    shutil.copyfile(case_dir / "results-hierarchy.yml", editorial_dir / "results-hierarchy.yml")
    editorial = load_document(case_dir / "editorial-model.yml")
    editorial["results_hierarchy"]["document"] = (
        "_paperops/model/editorial/results-hierarchy.yml"
    )
    _write_json(editorial_dir / "editorial-model.yml", editorial)
    visual_id = editorial["visual_obligations"][0]["id"]

    research_documents = _research_documents(visual_id)
    claim_hash = semantic_hash(research_documents[0], excluded_paths=HASH_EXCLUSIONS)
    result_hash = semantic_hash(research_documents[4], excluded_paths=HASH_EXCLUSIONS)

    section_document = section()
    section_document["status"] = "verified"
    section_document["editorial_move_refs"] = [editorial["argument_moves"][0]["id"]]
    block_document = block()
    block_document["status"] = "verified"
    block_document["compiled_from"]["input_hashes"] = [claim_hash, result_hash]
    block_document["dependencies"] = [
        {
            "target_id": "CLM-0001",
            "relation": "uses",
            "expected_revision": 1,
            "expected_hash": claim_hash,
        }
    ]

    _write_index(project, "research", research_documents)
    _write_index(project, "manuscript", [section_document, block_document])
    registry = load_registry(project)
    loaded = [
        load_model_document(project, registry.entries[name])
        for name in ("research", "manuscript")
    ]
    catalog = build_object_catalog(loaded)
    block_dependency_hash = dependency_hash("BLK-0001", catalog)
    empty_dependency_hash = dependency_hash("SEC-0001", catalog)
    block_document["dependency_hash"] = block_dependency_hash
    block_document["last_verified_dependency_hash"] = block_dependency_hash
    section_document["dependency_hash"] = empty_dependency_hash
    section_document["last_verified_dependency_hash"] = empty_dependency_hash
    _write_index(project, "manuscript", [section_document, block_document])

    issue_documents = [
        feedback(),
        analysis_request(),
        writing_request(),
        response(),
        review_round(),
    ]
    _write_index(project, "issue", issue_documents)

    all_loaded = [
        load_model_document(project, registry.entries[name])
        for name in ("research", "manuscript", "issue")
    ]
    catalog = build_object_catalog(all_loaded)
    publication_document = publication()
    snapshot = []
    for target_id in ("CLM-0001", "BLK-0001", "AREQ-0001", "RSP-0001"):
        target = catalog.objects[target_id]
        snapshot.append(
            {
                "target_id": target_id,
                "relation": "publication_input",
                "expected_revision": target.revision,
                "expected_hash": target.object_hash,
            }
        )
    candidate = publication_document["current_candidate"]
    candidate["snapshot_dependencies"] = snapshot
    candidate_hash = semantic_hash(candidate)
    publication_document["rounds"][0]["candidate_hash"] = candidate_hash
    publication_document["rounds"][0]["snapshot_dependencies"] = copy.deepcopy(snapshot)
    publication_document["submission_approvals"][0]["candidate_hash"] = candidate_hash
    _write_json(
        project / "_paperops/model/publication/publication-model.yml",
        publication_document,
    )
