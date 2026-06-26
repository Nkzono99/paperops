"""Path helpers for paperops project layouts."""

from __future__ import annotations

from pathlib import Path


def internal_file(root: Path, rel: str | Path) -> Path:
    normalized = Path(str(rel).strip("/").replace("\\", "/"))
    modern = root / "_paperops" / normalized
    if modern.exists():
        return modern
    legacy = root / normalized
    if legacy.exists():
        return legacy
    return modern
