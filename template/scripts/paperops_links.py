#!/usr/bin/env python3
"""Shared helpers for paperops link registry checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperops_paths import internal_path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


LINKS_REL_PATH = "refs/links.toml"
LOCAL_LOCATIONS_REL_PATH = "refs/local/locations.toml"
EXAMPLE_LOCATIONS_REL_PATH = "refs/local/locations.example.toml"
LINKS_DISPLAY_PATH = "_paperops/refs/links.toml"
LOCAL_LOCATIONS_DISPLAY_PATH = "_paperops/refs/local/locations.toml"
EXAMPLE_LOCATIONS_DISPLAY_PATH = "_paperops/refs/local/locations.example.toml"

ALLOWED_LINK_KINDS = {
    "runops_project",
    "directory",
    "dataset",
    "figure_source",
    "knowledge",
    "simulation",
}
ALLOWED_ACCESS = {"read", "read_write"}


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("TOML parsing requires Python 3.11 or newer.")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data if isinstance(data, dict) else {}


def paths_table(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = read_toml(path)
    paths = raw.get("paths", {})
    if not isinstance(paths, dict):
        return {}
    return {key: value for key, value in paths.items() if isinstance(value, dict)}


def link_registry_path(root: Path) -> Path:
    return internal_path(root, LINKS_REL_PATH)


def link_rows(raw: dict[str, Any]) -> list[Any] | None:
    rows = raw.get("links", [])
    return rows if isinstance(rows, list) else None


def link_dicts(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = link_rows(raw)
    if rows is None:
        return []
    return [row for row in rows if isinstance(row, dict)]


def link_map(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in link_dicts(raw):
        link_id = str(item.get("id", "")).strip()
        if link_id:
            rows[link_id] = item
    return rows


def local_locations(root: Path) -> dict[str, dict[str, Any]]:
    return paths_table(internal_path(root, LOCAL_LOCATIONS_REL_PATH))


def example_locations(root: Path) -> dict[str, dict[str, Any]]:
    return paths_table(internal_path(root, EXAMPLE_LOCATIONS_REL_PATH))


def resolve_local_path(root: Path, link: dict[str, Any], locations: dict[str, dict[str, Any]]) -> Path | None:
    location_ref = str(link.get("location_ref", "")).strip()
    if not location_ref or location_ref not in locations:
        return None
    raw_path = str(locations[location_ref].get("path", "")).strip()
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else root / path
