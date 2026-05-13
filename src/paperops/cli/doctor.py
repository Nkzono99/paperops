"""Health-check helpers for ``pops doctor`` and setup guidance."""

from __future__ import annotations

import shutil
from pathlib import Path

from paperops.cli.runtime import project_venv_python, uvx_pops_command


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
