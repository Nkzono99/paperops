"""Health-check helpers for ``pops doctor`` and setup guidance."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

from paperops.cli.runtime import project_venv_python, uvx_pops_command

LINK_REQUIRED_FIELDS = {
    "alias",
    "kind",
    "local_path_alias",
    "title",
    "description",
}


def check_uvx_available(warnings: list[str]) -> None:
    if shutil.which("uvx") is None and shutil.which("uv") is None:
        warnings.append(
            "uvx/uv is not on PATH; standard pops commands use "
            f"{uvx_pops_command('<command>')}."
        )


def check_project_venv_if_present(root: Path, warnings: list[str]) -> None:
    venv_dir = root / ".venv"
    if not venv_dir.exists():
        return
    if not project_venv_python(root).exists():
        warnings.append(".venv exists but its Python executable was not found.")


def print_manual_setup_hints(root: Path) -> None:
    if not (root / "refs" / "local" / "locations.toml").exists():
        print(
            "Manual: copy refs/local/locations.example.toml to "
            "refs/local/locations.toml when local paths are needed."
        )
    if not (root / "tex-env.toml").exists() and (root / "tex-env.example.toml").exists():
        print(
            "Optional: copy tex-env.example.toml to tex-env.toml when you need "
            "a custom TeX environment."
        )
    print("Run " + uvx_pops_command("doctor") + ".")


def check_path(root: Path, rel: str, errors: list[str]) -> None:
    if not (root / rel).exists():
        errors.append(f"missing {rel}")


def check_executable(name: str, warnings: list[str]) -> None:
    if shutil.which(name) is None:
        warnings.append(f"{name} is not on PATH")


def check_workflow_placeholders(root: Path, warnings: list[str]) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in sorted(workflows.glob("*.yml")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "YOUR_ORG/paperops" in text:
            warnings.append(f"workflow placeholder remains in {path.relative_to(root).as_posix()}")


def check_link_registry(root: Path, errors: list[str], warnings: list[str]) -> None:
    registry = root / "refs" / "links.toml"
    if not registry.exists():
        return

    try:
        data = tomllib.loads(registry.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"refs/links.toml is invalid TOML: {exc}")
        return

    links = data.get("links", [])
    if not isinstance(links, list):
        errors.append("refs/links.toml must contain [[links]] entries.")
        return

    aliases: set[str] = set()
    local_aliases: set[str] = set()
    for index, link in enumerate(links, start=1):
        if not isinstance(link, dict):
            errors.append(f"refs/links.toml entry {index} must be a table.")
            continue
        missing = sorted(field for field in LINK_REQUIRED_FIELDS if not link.get(field))
        alias = str(link.get("alias") or f"entry {index}")
        if missing:
            errors.append(
                f"refs/links.toml link {alias} is missing required fields: "
                + ", ".join(missing)
            )
        if alias in aliases:
            errors.append(f"refs/links.toml has duplicate alias: {alias}")
        aliases.add(alias)
        local_alias = link.get("local_path_alias")
        if isinstance(local_alias, str) and local_alias:
            local_aliases.add(local_alias)

    if not local_aliases:
        return

    local_locations = root / "refs" / "local" / "locations.toml"
    if not local_locations.exists():
        return

    try:
        locations = tomllib.loads(local_locations.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"refs/local/locations.toml is invalid TOML: {exc}")
        return

    paths = locations.get("paths", {})
    if not isinstance(paths, dict):
        warnings.append("refs/local/locations.toml has no [paths] aliases.")
        return

    missing_local = sorted(alias for alias in local_aliases if alias not in paths)
    if missing_local:
        warnings.append(
            "refs/links.toml local_path_alias values missing from "
            "refs/local/locations.toml: "
            + ", ".join(missing_local)
        )
