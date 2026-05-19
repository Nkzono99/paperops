from __future__ import annotations

import fnmatch
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.constants import EXCLUDED_SCAFFOLD_PATTERNS  # noqa: E402


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if self.target_name != "wheel":
            return

        filtered = Path(tempfile.mkdtemp(prefix="paperops-scaffold-"))
        copy_filtered_scaffold(Path(self.root) / "template", filtered)
        self.config["filtered_scaffold"] = str(filtered)
        build_data["force_include"][str(filtered)] = "paperops/_data/scaffold"

    def finalize(
        self, version: str, build_data: dict[str, Any], artifact_path: str
    ) -> None:
        self.clean([version])

    def clean(self, versions: list[str]) -> None:
        filtered = self.config.pop("filtered_scaffold", None)
        if filtered:
            shutil.rmtree(filtered, ignore_errors=True)


def copy_filtered_scaffold(source: Path, target: Path) -> None:
    for src in sorted(source.rglob("*")):
        rel = src.relative_to(source).as_posix()
        if is_excluded(rel):
            continue
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def is_excluded(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDED_SCAFFOLD_PATTERNS)
