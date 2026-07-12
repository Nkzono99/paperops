"""Registry-driven identities and semantic hashes for change planning."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


class CatalogError(ValueError):
    pass


def load_registry(root: Path) -> dict[str, Any]:
    path = root / "_paperops/defaults/schemas/registry.yml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        models = payload["models"]
    except (OSError, TypeError, KeyError, yaml.YAMLError) as exc:
        raise CatalogError("model registry is missing or invalid") from exc
    if not isinstance(models, dict):
        raise CatalogError("model registry is invalid")
    return models


def model_entry(root: Path, model: str) -> dict[str, Any]:
    entry = load_registry(root).get(model)
    if not isinstance(entry, dict):
        raise CatalogError(f"model `{model}` is not registered")
    return entry


def identity_for(root: Path, model: str, record_type: str, object_id: str) -> str:
    entry = model_entry(root, model)
    if entry.get("document_kind") == "aggregate":
        identity = entry.get("default_path")
    else:
        record_sets = entry.get("record_sets")
        record = record_sets.get(record_type) if isinstance(record_sets, dict) else None
        if not isinstance(record, dict) or re.fullmatch(str(record.get("id_pattern", "(?!)")), object_id) is None:
            raise CatalogError("record type or id is not admitted by the registry")
        identity = f"{record['path_prefix']}{object_id}.yml"
    path = PurePosixPath(str(identity))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CatalogError("registry produced an unsafe identity")
    return path.as_posix()


def index_identity(root: Path, model: str) -> str | None:
    entry = model_entry(root, model)
    return str(entry["default_path"]) if entry.get("document_kind") == "index" else None


def _remove_pointer(value: Any, pointer: str) -> None:
    if not pointer.startswith("/"):
        raise CatalogError("hash exclusion must be a JSON pointer")
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]
    parent = value
    for token in tokens[:-1]:
        if not isinstance(parent, dict) or token not in parent:
            return
        parent = parent[token]
    if isinstance(parent, dict):
        parent.pop(tokens[-1], None)


def semantic_hash(root: Path, model: str, record_type: str, document: dict[str, Any]) -> str:
    entry = model_entry(root, model)
    exclusions = entry.get("hash_excluded_paths", [])
    if entry.get("document_kind") == "index":
        exclusions = entry["record_sets"][record_type].get("hash_excluded_paths", [])
    detached = copy.deepcopy(document)
    for pointer in exclusions:
        _remove_pointer(detached, pointer)
    raw = json.dumps(detached, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def yaml_bytes(document: dict[str, Any]) -> bytes:
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")
