"""Paired Editorial and Results hierarchy migration without semantic guessing."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from paperops.model_validation import run_model_validation

from ..legacy import LegacyReadError, load_legacy_card
from ..types import (
    CandidateDocument,
    InventoryItem,
    MigrationCandidate,
    MigrationFinding,
    MigrationInput,
)


_EDITORIAL = Path("_paperops/model/editorial/editorial-model.yml")
_RESULTS = Path("_paperops/model/editorial/results-hierarchy.yml")
_STORYLINE = Path("_paperops/notes/views/storyline.md")


def _hash(value: Any, excluded: tuple[str, ...] = ()) -> str:
    normalized = copy.deepcopy(value)
    for pointer in excluded:
        current = normalized
        tokens = pointer.lstrip("/").split("/")
        for token in tokens[:-1]:
            current = current.get(token) if isinstance(current, dict) else None
        if isinstance(current, dict):
            current.pop(tokens[-1], None)
    payload = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _content(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("document must be a mapping")
    return value


class EditorialAdapter:
    adapter_version = 1

    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]:
        return self.materialize(migration_input).inventory

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate:
        root = migration_input.root.absolute()
        findings: list[MigrationFinding] = []
        documents: dict[str, dict[str, Any]] = {}
        sources: dict[str, Path] = {}

        typed_paths = {"editorial": _EDITORIAL, "results_hierarchy": _RESULTS}
        for model_name, relative in typed_paths.items():
            path = root / relative
            if not path.exists():
                continue
            validation = run_model_validation(root, model_name, phase="schema", strict=True)
            if not validation.ok:
                findings.extend(
                    MigrationFinding(
                        item.code,
                        item.pointer,
                        item.message,
                        item.severity,
                        relative.as_posix(),
                    )
                    for item in validation.findings
                )
                # A present malformed typed authority is never hidden by legacy fallback.
                return MigrationCandidate("editorial", (), (), tuple(findings))
            try:
                documents[model_name] = _load_yaml(path)
                sources[model_name] = path
            except (OSError, ValueError, yaml.YAMLError) as error:
                findings.append(
                    MigrationFinding(
                        "migration.malformed_typed",
                        f"/{model_name}",
                        f"typed document cannot be read: {error}",
                        source_path=relative.as_posix(),
                    )
                )
                return MigrationCandidate("editorial", (), (), tuple(findings))

        storyline_path = root / _STORYLINE
        if storyline_path.exists() or len(documents) != 2:
            try:
                storyline = load_legacy_card(storyline_path, project_root=root)
            except LegacyReadError as error:
                findings.append(
                    MigrationFinding(error.code, "/storyline", str(error), source_path=_STORYLINE.as_posix())
                )
                return MigrationCandidate("editorial", (), (), tuple(findings))
            for model_name in ("editorial", "results_hierarchy"):
                field_name = f"migration_{model_name}"
                field = storyline.frontmatter.get(field_name)
                if field is not None and isinstance(field.value, dict):
                    documents[model_name] = field.value
                    sources[model_name] = storyline_path
                    continue
                if model_name not in documents or model_name == "editorial":
                    findings.append(
                        MigrationFinding(
                            "migration.unresolved",
                            f"/frontmatter/{field_name}",
                            f"missing explicit `{field_name}` mapping; editorial choices are not inferred from prose",
                            source_path=_STORYLINE.as_posix(),
                        )
                    )
                    documents.pop(model_name, None)
                    sources.pop(model_name, None)

        if len(documents) != 2:
            return MigrationCandidate("editorial", (), (), tuple(findings))

        editorial = documents["editorial"]
        results = documents["results_hierarchy"]
        result_ids = [item.get("id") for item in results.get("items", []) if isinstance(item, dict)]
        referenced = editorial.get("results_hierarchy", {}).get("item_ids", [])
        if referenced != result_ids:
            findings.append(
                MigrationFinding(
                    "migration.unresolved",
                    "/results_hierarchy/item_ids",
                    "Editorial result order must exactly conserve the paired Results hierarchy",
                )
            )
        output = (
            CandidateDocument(
                _EDITORIAL.as_posix(),
                str(editorial.get("model_id", "editorial")),
                _hash(editorial, ("/metadata/updated_at",)),
                _content(editorial),
            ),
            CandidateDocument(
                _RESULTS.as_posix(),
                "results_hierarchy",
                _hash(results),
                _content(results),
            ),
        )
        inventory: list[InventoryItem] = []
        for model_name, document in documents.items():
            source = sources[model_name]
            raw = source.read_bytes()
            source_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
            target = (
                str(document.get("model_id", "editorial"))
                if model_name == "editorial"
                else "results_hierarchy"
            )
            inventory.append(
                InventoryItem(
                    family=f"{model_name}.document",
                    legacy_id=target,
                    source_path=source.relative_to(root).as_posix(),
                    pointer="/",
                    source_hash=source_hash,
                    disposition="mapped",
                    target_id=target,
                )
            )
        return MigrationCandidate("editorial", output, tuple(inventory), tuple(findings))
