"""Read and write ``.pops/manifest.toml``."""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paperops.cli.constants import (
    LAYOUT_VERSION,
    PACKAGE_NAME,
    UPGRADE_CHAIN_SUPPORTED_SINCE,
    UPSTREAM_REPO,
)
from paperops.cli.runtime import uvx_pops_command
from paperops.cli.versioning import minor_checkpoint, package_version


def applied_scaffold_version(root: Path) -> str | None:
    manifest = read_manifest(root / ".pops" / "manifest.toml")
    scaffold = manifest.get("scaffold")
    if not isinstance(scaffold, dict):
        return None
    version = scaffold.get("version")
    return version if isinstance(version, str) and version else None


def write_manifest(
    root: Path,
    *,
    template_ref: str = "",
    cli_install_spec: str | None = None,
) -> None:
    pops_dir = root / ".pops"
    pops_dir.mkdir(parents=True, exist_ok=True)
    manifest = pops_dir / "manifest.toml"
    existing = read_manifest(manifest)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    project = as_table(existing.get("project"))
    project["tool"] = "pops"
    project["updated_at"] = now

    scaffold = as_table(existing.get("scaffold"))
    scaffold["package"] = PACKAGE_NAME
    scaffold["version"] = package_version()
    scaffold["layout_version"] = LAYOUT_VERSION
    scaffold["source"] = UPSTREAM_REPO
    if template_ref:
        scaffold["template_ref"] = template_ref

    merged = dict(existing)
    merged["project"] = project
    merged["scaffold"] = scaffold
    merged["upgrade"] = upgrade_manifest_table(existing.get("upgrade"), now=now)
    merged["cli"] = cli_manifest_table(
        existing.get("cli"),
        now=now,
        legacy_install_spec=cli_install_spec,
    )

    manifest.write_text(dumps_manifest_toml(merged), encoding="utf-8")


def write_cli_metadata(root: Path) -> None:
    manifest = root / ".pops" / "manifest.toml"
    existing = read_manifest(manifest)
    if not existing:
        return
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    merged = dict(existing)
    merged["cli"] = cli_manifest_table(existing.get("cli"), now=now)
    manifest.write_text(dumps_manifest_toml(merged), encoding="utf-8")


def cli_manifest_table(
    existing: object,
    *,
    now: str,
    legacy_install_spec: str | None = None,
) -> dict[str, Any]:
    cli = as_table(existing)
    cli["package"] = PACKAGE_NAME
    cli["version"] = package_version()
    cli["runner"] = "uvx"
    cli["command"] = uvx_pops_command()
    cli["updated_at"] = now
    cli.pop("install_spec", None)
    cli.pop("venv", None)
    if legacy_install_spec is not None:
        cli["legacy_install_spec"] = legacy_install_spec
    return cli


def upgrade_manifest_table(existing: object, *, now: str) -> dict[str, Any]:
    upgrade = as_table(existing)
    upgrade["last_applied"] = package_version()
    upgrade["last_checkpoint"] = minor_checkpoint(package_version())
    upgrade["chain_supported_since"] = UPGRADE_CHAIN_SUPPORTED_SINCE
    upgrade["updated_at"] = now
    return upgrade


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def as_table(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def dumps_manifest_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in ordered_manifest_sections(data):
        value = data[section]
        if isinstance(value, dict):
            append_toml_table(lines, section, value)
        else:
            lines.append(f"{toml_key(section)} = {toml_value(value)}")
    return "\n".join(lines).rstrip() + "\n"


def ordered_manifest_sections(data: dict[str, Any]) -> list[str]:
    preferred = ["project", "scaffold", "upgrade", "cli"]
    return [item for item in preferred if item in data] + [
        item for item in data if item not in preferred
    ]


def append_toml_table(lines: list[str], name: str, table: dict[str, Any]) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"[{toml_dotted_key(name)}]")
    nested: list[tuple[str, dict[str, Any]]] = []
    for key, value in table.items():
        if isinstance(value, dict):
            nested.append((key, value))
        else:
            lines.append(f"{toml_key(key)} = {toml_value(value)}")
    for key, value in nested:
        append_toml_table(lines, f"{name}.{key}", value)


def toml_dotted_key(name: str) -> str:
    return ".".join(toml_key(part) for part in name.split("."))


def toml_key(key: str) -> str:
    if key and all(char.isascii() and (char.isalnum() or char in "_-") for char in key):
        return key
    return f'"{escape_toml(key)}"'


def toml_value(value: object) -> str:
    if isinstance(value, str):
        return f'"{escape_toml(value)}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    return f'"{escape_toml(str(value))}"'


def escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
