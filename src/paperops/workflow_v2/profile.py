"""Load the project-managed workflow profile without package fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paperops.compiler.privacy import scan_private_material
from paperops.compiler.safe_fs import SafeCaptureError, SafeProjectReader
from paperops.workflow_v2.types import MACRO_STAGES


PROFILE_IDENTITY = "_paperops/defaults/workflow/profile.yml"
_TOP_KEYS = frozenset({"profile_version", "macro_stages", "routes", "approval_kinds", "target_routes", "impact_relations"})


class WorkflowProfileError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowProfile:
    version: int
    macro_stages: tuple[str, ...]
    routes: tuple[str, ...]
    approval_kinds: tuple[str, ...]
    target_routes: tuple[tuple[str, str], ...]
    impact_relations: tuple[str, ...]

    def route_for(self, target_type: str) -> str:
        return dict(self.target_routes).get(target_type, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_version": self.version,
            "macro_stages": list(self.macro_stages),
            "routes": list(self.routes),
            "approval_kinds": list(self.approval_kinds),
            "target_routes": dict(self.target_routes),
            "impact_relations": list(self.impact_relations),
        }


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(row, str) and row for row in value):
        raise WorkflowProfileError(f"{label} must be a non-empty string list")
    if len(set(value)) != len(value):
        raise WorkflowProfileError(f"{label} contains duplicates")
    return tuple(value)


def load_workflow_profile(root: Path) -> WorkflowProfile:
    try:
        with SafeProjectReader(root) as reader:
            content = reader.read_bytes(PROFILE_IDENTITY)
    except (OSError, SafeCaptureError) as exc:
        raise WorkflowProfileError("managed workflow profile is missing or unsafe") from exc
    try:
        raw = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise WorkflowProfileError("managed workflow profile is invalid") from exc
    if not isinstance(raw, dict) or set(raw) != _TOP_KEYS or not all(isinstance(key, str) for key in raw):
        raise WorkflowProfileError("managed workflow profile has unknown or missing fields")
    if scan_private_material(raw):
        raise WorkflowProfileError("managed workflow profile contains private material")
    if raw["profile_version"] != 1:
        raise WorkflowProfileError("unsupported workflow profile version")
    stages = _strings(raw["macro_stages"], "macro_stages")
    if stages != MACRO_STAGES:
        raise WorkflowProfileError("macro_stages must use the fixed five-stage projection")
    routes = _strings(raw["routes"], "routes")
    kinds = _strings(raw["approval_kinds"], "approval_kinds")
    relations = _strings(raw["impact_relations"], "impact_relations")
    target_routes = raw["target_routes"]
    if not isinstance(target_routes, dict) or not target_routes or not all(isinstance(k, str) and isinstance(v, str) and v in routes for k, v in target_routes.items()):
        raise WorkflowProfileError("target_routes must map target types to registered routes")
    return WorkflowProfile(1, stages, routes, kinds, tuple(sorted(target_routes.items())), relations)
