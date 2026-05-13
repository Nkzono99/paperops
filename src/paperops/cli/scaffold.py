"""Scaffold source, copy, and managed-update planning."""

from __future__ import annotations

import fnmatch
import importlib.resources
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from paperops.cli.constants import EXCLUDED_SCAFFOLD_PATTERNS, MANAGED_UPDATE_PATTERNS
from paperops.cli.manifest import write_manifest
from paperops.cli.models import CopyPlan


@contextmanager
def scaffold_source() -> Iterator[Path]:
    dev_source = Path(__file__).resolve().parents[3] / "template"
    if dev_source.is_dir():
        yield dev_source
        return

    package_source = importlib.resources.files("paperops") / "_data" / "scaffold"
    with importlib.resources.as_file(package_source) as source:
        yield source


@contextmanager
def source_dir_context(source: Path | None) -> Iterator[Path]:
    if source is not None:
        resolved = source.expanduser().resolve()
        if not resolved.is_dir():
            raise SystemExit(f"source directory not found: {resolved}")
        yield resolved
    else:
        with scaffold_source() as bundled:
            yield bundled


def copy_scaffold(source: Path, target: Path, *, overwrite: bool) -> CopyPlan:
    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    excluded: list[str] = []

    for src in sorted(source.rglob("*")):
        rel = normalize_rel(src.relative_to(source))
        if is_excluded(rel):
            excluded.append(rel)
            continue
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
            missing.append(rel)
        elif same_file_content(src, dst):
            unchanged.append(rel)
        elif overwrite:
            shutil.copy2(src, dst)
            changed.append(rel)
        else:
            changed.append(rel)
    return CopyPlan(missing=missing, changed=changed, unchanged=unchanged, excluded=excluded)


def plan_managed_update(
    source: Path,
    root: Path,
    *,
    only_prefixes: list[str] | None = None,
) -> CopyPlan:
    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    excluded: list[str] = []
    for src in sorted(source.rglob("*")):
        rel = normalize_rel(src.relative_to(source))
        if src.is_dir():
            continue
        if (
            is_excluded(rel)
            or not is_managed_update(rel)
            or not path_requested(rel, only_prefixes)
        ):
            excluded.append(rel)
            continue
        dst = root / rel
        if not dst.exists():
            missing.append(rel)
        elif same_file_content(src, dst):
            unchanged.append(rel)
        else:
            changed.append(rel)
    return CopyPlan(missing=missing, changed=changed, unchanged=unchanged, excluded=excluded)


def apply_managed_update(
    source: Path,
    root: Path,
    plan: CopyPlan,
    *,
    overwrite: bool,
    template_ref: str = "",
) -> int:
    candidates = list(plan.missing)
    if overwrite:
        candidates.extend(plan.changed)

    for rel in candidates:
        src = source / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if candidates:
        write_manifest(root, template_ref=template_ref)
    return len(candidates)


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def is_excluded(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDED_SCAFFOLD_PATTERNS)


def is_managed_update(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in MANAGED_UPDATE_PATTERNS)


def path_requested(rel: str, only_prefixes: list[str] | None) -> bool:
    if only_prefixes is None:
        return True
    return any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in only_prefixes)


def parse_only(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    prefixes = [item.strip().strip("/").replace("\\", "/") for item in raw.split(",")]
    return [item for item in prefixes if item]


def same_file_content(left: Path, right: Path) -> bool:
    try:
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False
