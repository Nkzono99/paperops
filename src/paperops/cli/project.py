"""Project root discovery and setup-target helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from paperops.cli.constants import PROJECT_MARKERS


def detect_template_ref(source: Path | None) -> str:
    if source is None:
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".pops" / "manifest.toml").exists():
            return candidate
        if all((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def resolve_setup_target(url_or_path: str | None, explicit_path: Path | None) -> Path:
    if url_or_path is None:
        return explicit_path or Path.cwd()

    candidate = Path(url_or_path).expanduser()
    if explicit_path is None and candidate.exists():
        return candidate

    return clone_project(url_or_path, explicit_path)


def clone_project(url: str, dest: Path | None) -> Path:
    target = (dest or Path.cwd() / repo_name_from_url(url)).expanduser().resolve()
    if target.exists():
        print(f"error: destination already exists: {target}", file=sys.stderr)
        raise SystemExit(2)
    print(f"Cloning {url} ...")
    result = subprocess.run(
        ["git", "clone", url, str(target)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        print(f"error: git clone failed: {message[:300]}", file=sys.stderr)
        raise SystemExit(1)
    return target


def repo_name_from_url(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if ":" in name and not name.startswith("http"):
        name = name.rsplit(":", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "paper-project"
