"""Runtime command helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from paperops.cli.constants import PACKAGE_NAME


def uvx_pops_command(*pops_args: str) -> str:
    command = ["uvx", "--from", PACKAGE_NAME, "pops", *pops_args]
    return " ".join(command)


def project_venv_python(root: Path) -> Path:
    if sys.platform.startswith("win"):
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"
