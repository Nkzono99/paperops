"""Parse the closed, path-confined PaperOps change request format."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from paperops.compiler.privacy import scan_private_material
from paperops.model_state import HASH_PATTERN, MODEL_NAMES

from .types import ChangeRequest, Operation, frozen_mapping


_REQUEST_KEYS = {"schema_version", "reason", "operations"}
_OPERATION_KEYS = {
    "action", "model", "record_type", "id", "expected_revision",
    "expected_hash", "document",
}
_INDEX_RECORDS = {
    "research": {"claim", "result", "figure", "source", "scientific_gate"},
    "manuscript": {"section", "block"},
    "issue": {
        "feedback", "analysis_request", "writing_request", "response",
        "review_round", "workflow_issue",
    },
}
_AGGREGATE_RECORDS = {
    "editorial": "editorial",
    "results_hierarchy": "results_hierarchy",
    "publication": "publication",
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ChangeRequestError(ValueError):
    """A change request is unsafe, ambiguous, or outside the public schema."""


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ChangeRequestError(f"{label} must be a string-keyed mapping")
    return value


def _load_document(request_path: Path, value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return _mapping(value, "operation.document")
    if not isinstance(value, str):
        raise ChangeRequestError("operation.document must be a mapping or relative YAML/JSON file")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ChangeRequestError("operation.document path must be confined below the request directory")
    candidate = request_path.parent.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=True).relative_to(request_path.parent.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ChangeRequestError("operation.document path is missing or escapes the request directory") from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise ChangeRequestError("operation.document path must name a regular file")
    try:
        raw = candidate.read_text(encoding="utf-8")
        loaded = json.loads(raw) if candidate.suffix == ".json" else yaml.safe_load(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ChangeRequestError("operation.document file is invalid") from exc
    return _mapping(loaded, "operation.document")


def _operation(request_path: Path, value: object) -> Operation:
    row = _mapping(value, "operation")
    unknown = set(row) - _OPERATION_KEYS
    if unknown:
        raise ChangeRequestError(f"operation has unknown fields: {', '.join(sorted(unknown))}")
    action = row.get("action")
    model = row.get("model")
    record_type = row.get("record_type")
    object_id = row.get("id")
    if action not in {"upsert", "delete"}:
        raise ChangeRequestError("operation.action must be upsert or delete")
    if model not in MODEL_NAMES:
        raise ChangeRequestError("operation.model is unknown")
    if not isinstance(record_type, str) or (
        record_type not in _INDEX_RECORDS.get(model, set())
        and record_type != _AGGREGATE_RECORDS.get(model)
    ):
        raise ChangeRequestError("operation.record_type is not registered for the model")
    if not isinstance(object_id, str) or _SAFE_ID.fullmatch(object_id) is None:
        raise ChangeRequestError("operation.id is unsafe")
    revision = row.get("expected_revision")
    digest = row.get("expected_hash", "")
    if revision is not None and (type(revision) is not int or revision < 0):
        raise ChangeRequestError("operation.expected_revision must be a non-negative integer or null")
    if not isinstance(digest, str) or (digest and HASH_PATTERN.fullmatch(digest) is None):
        raise ChangeRequestError("operation.expected_hash must be empty or sha256:<hex>")
    existing = revision is not None or bool(digest)
    if existing and (revision is None or not digest):
        raise ChangeRequestError("existing records require revision and hash preconditions")
    if action == "delete" and not existing:
        raise ChangeRequestError("delete requires revision and hash preconditions")
    document = None
    if action == "upsert":
        if "document" not in row:
            raise ChangeRequestError("upsert requires a candidate document")
        document = _load_document(request_path, row["document"])
        if document.get("id", object_id) != object_id:
            raise ChangeRequestError("candidate document id disagrees with operation.id")
    elif "document" in row:
        raise ChangeRequestError("delete must not contain a candidate document")
    candidate_revision = document.get("revision") if document is not None else None
    return Operation(
        action,
        model,
        record_type,
        object_id,
        revision,
        digest,
        frozen_mapping(document) if document is not None else None,
        candidate_revision if isinstance(candidate_revision, int) else None,
    )


def load_change_request(path: Path) -> ChangeRequest:
    """Load a request without retaining its local path or unsafe source material."""
    path = path.expanduser()
    if path.is_symlink() or not path.is_file():
        raise ChangeRequestError("change request must be a regular YAML or JSON file")
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(raw) if path.suffix == ".json" else yaml.safe_load(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ChangeRequestError("change request is invalid") from exc
    payload = _mapping(loaded, "request")
    unknown = set(payload) - _REQUEST_KEYS
    if unknown:
        raise ChangeRequestError(f"request has unknown fields: {', '.join(sorted(unknown))}")
    if payload.get("schema_version") != 1:
        raise ChangeRequestError("request.schema_version must be 1")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ChangeRequestError("request.reason must be non-empty public text")
    rows = payload.get("operations")
    if not isinstance(rows, list) or not rows:
        raise ChangeRequestError("request.operations must be a non-empty array")
    operations = tuple(_operation(path, row) for row in rows)
    identities = [(item.model, item.object_id) for item in operations]
    if len(set(identities)) != len(identities):
        raise ChangeRequestError("request contains duplicate model/object operations")
    public_projection = {
        "reason": reason,
        "operations": [
            {
                "model": item.model,
                "record_type": item.record_type,
                "id": item.object_id,
                "document": dict(item.document) if item.document is not None else None,
            }
            for item in operations
        ],
    }
    if scan_private_material(public_projection):
        raise ChangeRequestError("change request contains private or credential material")
    return ChangeRequest(1, reason.strip(), operations)
