"""Deterministic, non-ranking comparison of verified compile bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .bundles import load_verified_bundle
from .types import _freeze_json, _json_compatible


@dataclass(frozen=True)
class CompileComparison:
    left_compile_id: str
    right_compile_id: str
    changes: tuple[Mapping[str, Any], ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "changes", tuple(_freeze_json(row) for row in self.changes))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "left_compile_id": self.left_compile_id,
            "right_compile_id": self.right_compile_id,
            "changes": [_json_compatible(row) for row in self.changes],
        }


def _projection(bundle: Mapping[str, Any]) -> dict[str, object]:
    context = bundle.get("global_context", {})
    request = bundle.get("request", {})
    return {
        "selected_story": context.get("selected_story", {}),
        "rejected_stories": context.get("rejected_stories", []),
        "move_order": context.get("ordered_moves", []),
        "claim_roles": context.get("claim_roles", {}),
        "result_order": context.get("evidence_ladder", []),
        "section_placement": context.get("section_block_map", []),
        "visual_obligations": context.get("visual_obligations", []),
        "targets": request.get("targets", []),
        "write_scope": request.get("write_scope", {}),
    }


def compare_bundles(
    root: str | Path,
    left_id: str,
    right_id: str,
) -> CompileComparison:
    left = _projection(load_verified_bundle(root, left_id).bundle)
    right = _projection(load_verified_bundle(root, right_id).bundle)
    changes = tuple(
        {
            "field": field,
            "left": _json_compatible(left[field]),
            "right": _json_compatible(right[field]),
        }
        for field in left
        if left[field] != right[field]
    )
    return CompileComparison(left_id, right_id, changes)


__all__ = ["CompileComparison", "compare_bundles"]
