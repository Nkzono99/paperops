"""Bounded inventory of the legacy workflow authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paperops.compiler.safe_fs import SafeProjectReader


@dataclass(frozen=True)
class WorkflowMigrationInventory:
    source_hash: str
    overall_state: str
    concerns: tuple[Any, ...]
    concern_count: int
    legacy_identities: tuple[str, ...]


def inventory_legacy_workflow(root: Path) -> WorkflowMigrationInventory:
    identities = ("_paperops/workflow/current-state.yml", "_paperops/workflow/round-summary.yml")
    captured = []
    with SafeProjectReader(root) as reader:
        for identity in identities:
            item = reader.read_optional_file(identity)
            if item is not None:
                captured.append(item)
    if not captured:
        raise ValueError("legacy workflow state is missing")
    documents: dict[str, dict[str, Any]] = {}
    hashes = []
    for content, metadata in captured:
        try:
            value = yaml.safe_load(content.decode("utf-8"))
        except (UnicodeError, yaml.YAMLError) as exc:
            raise ValueError("legacy workflow state is invalid") from exc
        if not isinstance(value, dict):
            raise ValueError("legacy workflow state must be a mapping")
        documents[metadata.identity] = value
        hashes.append((metadata.identity, metadata.content_hash))
    current = documents.get(identities[0], {})
    review = current.get("review", {})
    concerns: list[Any] = []
    if isinstance(review, dict):
        for key in ("blocking_concerns", "major_concerns"):
            rows = review.get(key, [])
            if isinstance(rows, list):
                concerns.extend(rows)
    overall = current.get("overall", {})
    state = overall.get("state", "") if isinstance(overall, dict) else ""
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return WorkflowMigrationInventory(f"sha256:{digest}", str(state), tuple(concerns), len(concerns), tuple(row[0] for row in hashes))
