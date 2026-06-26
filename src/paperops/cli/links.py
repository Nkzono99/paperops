"""Link registry helpers for paper draft projects."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops.cli.paths import internal_file

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - package requires 3.11+, kept for clearer import errors
    tomllib = None  # type: ignore[assignment]

TomlDecodeError = tomllib.TOMLDecodeError if tomllib is not None else ValueError

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


@dataclass(frozen=True)
class LinkFinding:
    severity: str
    message: str


@dataclass(frozen=True)
class LinkRegistry:
    path: Path
    links: tuple[dict[str, Any], ...]
    schema_version: int | None = None


def _read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("TOML parsing requires Python 3.11 or newer.")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        return {}
    return data


def _paths_table(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = _read_toml(path)
    paths = raw.get("paths", {})
    if not isinstance(paths, dict):
        return {}
    return {key: value for key, value in paths.items() if isinstance(value, dict)}


def load_link_registry(root: Path) -> LinkRegistry | None:
    path = internal_file(root, LINKS_REL_PATH)
    if not path.exists():
        return None
    raw = _read_toml(path)
    links = raw.get("links", [])
    if not isinstance(links, list):
        links = []
    return LinkRegistry(
        path=path,
        schema_version=raw.get("schema_version"),
        links=tuple(item for item in links if isinstance(item, dict)),
    )


def validate_link_registry(root: Path, *, strict_local: bool = False) -> list[LinkFinding]:
    findings: list[LinkFinding] = []
    registry_path = internal_file(root, LINKS_REL_PATH)
    if not registry_path.exists():
        return findings

    try:
        raw = _read_toml(registry_path)
    except (OSError, TomlDecodeError) as exc:
        return [
            LinkFinding("error", f"`{LINKS_DISPLAY_PATH}` を TOML として読めません: {exc}")
        ]

    schema_version = raw.get("schema_version")
    if schema_version != 1:
        findings.append(
            LinkFinding(
                "error",
                f"`{LINKS_DISPLAY_PATH}` の `schema_version` は 1 である必要があります",
            )
        )

    raw_links = raw.get("links", [])
    if not isinstance(raw_links, list):
        findings.append(LinkFinding("error", f"`{LINKS_DISPLAY_PATH}` の `links` は配列にしてください"))
        raw_links = []

    local_locations = _paths_table(internal_file(root, LOCAL_LOCATIONS_REL_PATH))
    example_locations = _paths_table(internal_file(root, EXAMPLE_LOCATIONS_REL_PATH))
    has_local_locations = bool(local_locations)

    seen_ids: set[str] = set()
    for index, item in enumerate(raw_links, start=1):
        if not isinstance(item, dict):
            findings.append(LinkFinding("error", f"`links[{index}]` は table にしてください"))
            continue

        link_id = str(item.get("id", "")).strip()
        kind = str(item.get("kind", "")).strip()
        location_ref = str(item.get("location_ref", "")).strip()
        access = str(item.get("access", "read")).strip() or "read"

        if not link_id:
            findings.append(LinkFinding("error", f"`links[{index}]` に `id` がありません"))
        elif link_id in seen_ids:
            findings.append(LinkFinding("error", f"`{LINKS_DISPLAY_PATH}` の link id `{link_id}` が重複しています"))
        else:
            seen_ids.add(link_id)

        if kind not in ALLOWED_LINK_KINDS:
            findings.append(
                LinkFinding(
                    "error",
                    f"`{link_id or f'links[{index}]'}` の kind `{kind}` は未知です",
                )
            )

        if not location_ref:
            findings.append(LinkFinding("error", f"`{link_id or f'links[{index}]'}` に `location_ref` がありません"))
            continue

        if access not in ALLOWED_ACCESS:
            findings.append(
                LinkFinding(
                    "error",
                    f"`{link_id or f'links[{index}]'}` の access は `read` または `read_write` にしてください",
                )
            )

        if example_locations and location_ref not in example_locations:
            findings.append(
                LinkFinding(
                    "warning",
                    f"`{link_id or location_ref}` の location_ref `{location_ref}` が `{EXAMPLE_LOCATIONS_DISPLAY_PATH}` にありません",
                )
            )
        if has_local_locations and location_ref not in local_locations:
            findings.append(
                LinkFinding(
                    "warning",
                    f"`{link_id or location_ref}` の location_ref `{location_ref}` が `{LOCAL_LOCATIONS_DISPLAY_PATH}` にありません",
                )
            )

    if strict_local and raw_links and not has_local_locations:
        findings.append(
            LinkFinding(
                "warning",
                f"`{LOCAL_LOCATIONS_DISPLAY_PATH}` がないため link の実パスは解決できません",
            )
        )

    return findings


def iter_links(root: Path, *, resolve_local: bool = False) -> list[dict[str, Any]]:
    registry = load_link_registry(root)
    if registry is None:
        return []
    local_locations = _paths_table(internal_file(root, LOCAL_LOCATIONS_REL_PATH)) if resolve_local else {}
    rows: list[dict[str, Any]] = []
    for link in registry.links:
        row = dict(link)
        location_ref = str(row.get("location_ref", "")).strip()
        if resolve_local and location_ref in local_locations:
            row["local_path"] = str(local_locations[location_ref].get("path", ""))
            row["local_host"] = str(local_locations[location_ref].get("host", ""))
        rows.append(row)
    return rows
