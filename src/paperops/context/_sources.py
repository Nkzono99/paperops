"""Discover research sources and their analysis topics."""

from __future__ import annotations

import time
from pathlib import Path

from paperops.project import Source

_MAX_TOPICS = 40
_RUN_TREE_DEPTH = 5


def _day(path: Path) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))


def _analysis_topics(source: Source) -> list[str]:
    """READMEs of analysis topics in a runops project (project-wide and per run group)."""
    root = source.path
    topics = sorted((root / "analysis").glob("*/README.md")) if (root / "analysis").is_dir() else []

    def walk(directory: Path, depth: int) -> None:
        if depth > _RUN_TREE_DEPTH or len(topics) >= _MAX_TOPICS:
            return
        try:
            children = sorted(p for p in directory.iterdir() if p.is_dir())
        except OSError:
            return
        for child in children:
            if child.name == "_analysis":
                topics.extend(sorted(child.glob("*/README.md")))
            elif child.name.startswith(("_", ".")) or (child / "manifest.toml").is_file():
                continue  # archive, scratch and run directories are not searched
            else:
                walk(child, depth + 1)

    if (root / "runs").is_dir():
        walk(root / "runs", 1)
    return [str(p.relative_to(root)) for p in topics[:_MAX_TOPICS]]


def source_state(source: Source) -> dict:
    exists = source.path.is_dir()
    log = source.path / "LOG.md"
    return {
        "name": source.name,
        "path": str(source.path),
        "note": source.note,
        "exists": exists,
        "runops": exists and source.is_runops,
        "log_updated": _day(log) if log.is_file() else "",
        "analysis": _analysis_topics(source) if exists else [],
    }
