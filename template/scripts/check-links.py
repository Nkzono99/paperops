#!/usr/bin/env python3

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_paths import display_path, internal_path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


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


@dataclass
class Finding:
    severity: str
    message: str


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


def add(findings: list[Finding], severity: str, message: str) -> None:
    findings.append(Finding(severity=severity, message=message))


def check_links(root: Path, *, strict_local: bool) -> list[Finding]:
    findings: list[Finding] = []
    registry_path = internal_path(root, LINKS_REL_PATH)
    if not registry_path.exists():
        return findings

    try:
        raw = read_toml(registry_path)
    except Exception as exc:
        return [Finding("error", f"`{display_path(root, registry_path)}` を TOML として読めません: {exc}")]

    if raw.get("schema_version") != 1:
        add(findings, "error", f"`{display_path(root, registry_path)}` の `schema_version` は 1 である必要があります")

    links = raw.get("links", [])
    if not isinstance(links, list):
        add(findings, "error", f"`{display_path(root, registry_path)}` の `links` は配列にしてください")
        links = []

    local_locations = paths_table(internal_path(root, LOCAL_LOCATIONS_REL_PATH))
    example_locations = paths_table(internal_path(root, EXAMPLE_LOCATIONS_REL_PATH))
    has_local_locations = bool(local_locations)
    seen_ids: set[str] = set()

    for index, item in enumerate(links, start=1):
        if not isinstance(item, dict):
            add(findings, "error", f"`links[{index}]` は table にしてください")
            continue

        link_id = str(item.get("id", "")).strip()
        kind = str(item.get("kind", "")).strip()
        location_ref = str(item.get("location_ref", "")).strip()
        access = str(item.get("access", "read")).strip() or "read"
        label = link_id or f"links[{index}]"

        if not link_id:
            add(findings, "error", f"`links[{index}]` に `id` がありません")
        elif link_id in seen_ids:
            add(findings, "error", f"`{display_path(root, registry_path)}` の link id `{link_id}` が重複しています")
        else:
            seen_ids.add(link_id)

        if kind not in ALLOWED_LINK_KINDS:
            add(findings, "error", f"`{label}` の kind `{kind}` は未知です")
        if access not in ALLOWED_ACCESS:
            add(findings, "error", f"`{label}` の access は `read` または `read_write` にしてください")
        if not location_ref:
            add(findings, "error", f"`{label}` に `location_ref` がありません")
            continue
        if example_locations and location_ref not in example_locations:
            add(
                findings,
                "warning",
                f"`{label}` の location_ref `{location_ref}` が `{EXAMPLE_LOCATIONS_DISPLAY_PATH}` にありません",
            )
        if has_local_locations and location_ref not in local_locations:
            add(
                findings,
                "warning",
                f"`{label}` の location_ref `{location_ref}` が `{LOCAL_LOCATIONS_DISPLAY_PATH}` にありません",
            )

    if strict_local and links and not has_local_locations:
        add(findings, "warning", f"`{LOCAL_LOCATIONS_DISPLAY_PATH}` がないため link の実パスは解決できません")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="_paperops/refs/links.toml の link registry を検証する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--strict-local",
        action="store_true",
        help="_paperops/refs/local/locations.toml がない場合に warning を出す。",
    )
    args = parser.parse_args()

    findings = check_links(args.root.resolve(), strict_local=args.strict_local)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# links-check")
    print("")
    if errors:
        print("## Errors")
        for finding in errors:
            print(f"- {finding.message}")
        print("")
    if warnings:
        print("## Warnings")
        for finding in warnings:
            print(f"- {finding.message}")
        print("")
    if not findings:
        print("link registry に問題は見つかりませんでした。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
