"""Read-only typed model accessors shared by legacy-named public check commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


class TypedViewError(ValueError):
    pass


@dataclass(frozen=True)
class TypedDocument:
    model: str
    record_type: str
    object_id: str
    path: Path
    document: dict[str, Any]


INDEXES = {
    "research": "_paperops/model/research/index.yml",
    "manuscript": "_paperops/model/manuscript/index.yml",
    "issue": "_paperops/model/issues/index.yml",
}
AGGREGATES = {
    "editorial": "_paperops/model/editorial/editorial-model.yml",
    "results_hierarchy": "_paperops/model/editorial/results-hierarchy.yml",
    "publication": "_paperops/model/publication/publication-model.yml",
}


def load_mapping(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise TypedViewError(f"typed document is missing: {path.name}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise TypedViewError(f"typed document is invalid: {path.name}") from exc
    if not isinstance(value, dict):
        raise TypedViewError(f"typed document must be a mapping: {path.name}")
    return value


def indexed_documents(root: Path, model: str, record_type: str | None = None) -> tuple[TypedDocument, ...]:
    identity = INDEXES.get(model)
    if identity is None:
        raise TypedViewError(f"unknown indexed model: {model}")
    index = load_mapping(root / identity)
    records = index.get("records")
    if not isinstance(records, list):
        raise TypedViewError(f"typed {model} index records must be an array")
    result = []
    seen = set()
    for row in records:
        if not isinstance(row, dict) or not all(isinstance(row.get(key), str) for key in ("id", "record_type", "document")):
            raise TypedViewError(f"typed {model} index row is invalid")
        if record_type is not None and row["record_type"] != record_type:
            continue
        relative = PurePosixPath(row["document"])
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise TypedViewError(f"typed {model} index path is unsafe")
        path = root.joinpath(*relative.parts)
        document = load_mapping(path)
        if document.get("id") != row["id"] or document.get("record_type") != row["record_type"] or row["id"] in seen:
            raise TypedViewError(f"typed {model} index identity is inconsistent")
        seen.add(row["id"])
        result.append(TypedDocument(model, row["record_type"], row["id"], path, document))
    return tuple(result)


def aggregate_document(root: Path, model: str) -> TypedDocument:
    identity = AGGREGATES.get(model)
    if identity is None:
        raise TypedViewError(f"unknown aggregate model: {model}")
    path = root / identity
    document = load_mapping(path)
    object_id = str(document.get("model_id") or model)
    return TypedDocument(model, model, object_id, path, document)


def workflow_projection(root: Path) -> dict[str, Any]:
    """Project coarse workflow axes from typed authority; never read macro-state files."""
    sections = indexed_documents(root, "manuscript", "section")
    issues = indexed_documents(root, "issue")
    publication = aggregate_document(root, "publication").document
    open_issues = [item for item in issues if item.document.get("status") not in {"closed", "superseded", "resolved"}]
    section_states = {str(item.document.get("section_kind")): str(item.document.get("status", "")) for item in sections}
    return {
        "stage": "blocked" if open_issues else ("drafting" if sections else "scoped"),
        "sections": section_states,
        "submission": str(publication.get("submission_state", "authoring")),
        "open_issue_ids": [item.object_id for item in open_issues],
    }
