#!/usr/bin/env python3
"""Path helpers for the versioned paperops internal surface."""

from __future__ import annotations

from pathlib import Path


INTERNAL_ROOT = "_paperops"
DEFAULTS_ROOT = "_paperops/defaults"
LEGACY_INTERNAL_DIRS = {
    "claims",
    "contracts",
    "evidence",
    "notes/views",
    "refs",
    "requests",
    "review",
    "workflow",
}


def internal_path(root: Path, *parts: str) -> Path:
    """Return the preferred path for versioned internal paperops state."""

    rel = _relative_path(*parts)
    modern = root / INTERNAL_ROOT / rel
    defaults = root / DEFAULTS_ROOT / rel
    legacy = root / rel
    if modern.exists():
        return modern
    if defaults.exists():
        return defaults
    if legacy.exists():
        return legacy
    return modern


def required_internal_path(root: Path, *parts: str) -> Path:
    """Return an existing internal path or the preferred modern location."""

    path = internal_path(root, *parts)
    if path.exists():
        return path
    return root / INTERNAL_ROOT / _relative_path(*parts)


def internal_glob(root: Path, pattern: str) -> list[Path]:
    """Glob internal files, preferring `_paperops/` over legacy roots."""

    normalized = pattern.strip("/").replace("\\", "/")
    modern_root = root / INTERNAL_ROOT
    defaults_root = root / DEFAULTS_ROOT
    modern_matches = sorted(modern_root.glob(normalized)) if modern_root.exists() else []
    if modern_matches:
        return modern_matches
    defaults_matches = sorted(defaults_root.glob(normalized)) if defaults_root.exists() else []
    if defaults_matches:
        return defaults_matches
    return sorted(root.glob(normalized))


def display_path(root: Path, path: Path) -> str:
    """Return a stable POSIX-style path for diagnostics."""

    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _relative_path(*parts: str) -> Path:
    rel = Path()
    for part in parts:
        normalized = part.strip("/").replace("\\", "/")
        if normalized:
            rel /= Path(normalized)
    return rel
