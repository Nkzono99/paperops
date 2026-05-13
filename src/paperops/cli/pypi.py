"""PyPI lookup and update-check cache helpers."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from paperops.cli.constants import (
    PACKAGE_NAME,
    PYPI_JSON_URL,
    UPDATE_CHECK_INTERVAL_SECONDS,
)
from paperops.cli.versioning import (
    package_version,
    release_version_tuple,
    sorted_versions,
)


def latest_package_version() -> str | None:
    now = time.time()
    cached = read_update_check_cache()
    if cached is not None:
        checked_at = as_float(cached.get("checked_at"))
        latest = cached.get("latest_version")
        if (
            isinstance(latest, str)
            and checked_at is not None
            and now - checked_at < UPDATE_CHECK_INTERVAL_SECONDS
        ):
            return latest
        if (
            latest is None
            and checked_at is not None
            and now - checked_at < UPDATE_CHECK_INTERVAL_SECONDS
        ):
            return None

    latest = fetch_latest_package_version()
    if latest is not None:
        write_update_check_cache({"checked_at": now, "latest_version": latest})
        return latest
    write_update_check_cache({"checked_at": now})
    return None


def available_package_versions() -> list[str]:
    versions = fetch_available_package_versions()
    if versions:
        return versions
    current = package_version()
    latest = latest_package_version()
    candidates = [current]
    if latest is not None:
        candidates.append(latest)
    return sorted_versions(candidates)


def fetch_latest_package_version() -> str | None:
    request = urllib.request.Request(
        PYPI_JSON_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": f"pops/{package_version()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, json.JSONDecodeError, urllib.error.URLError):
        return None
    info = data.get("info") if isinstance(data, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    return version if isinstance(version, str) and version else None


def fetch_available_package_versions() -> list[str]:
    request = urllib.request.Request(
        PYPI_JSON_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": f"pops/{package_version()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, json.JSONDecodeError, urllib.error.URLError):
        return []
    releases = data.get("releases") if isinstance(data, dict) else None
    if not isinstance(releases, dict):
        return []
    candidates: list[str] = []
    for version, files in releases.items():
        if not release_version_tuple(version):
            continue
        if isinstance(files, list) and files and all(
            isinstance(item, dict) and item.get("yanked") for item in files
        ):
            continue
        candidates.append(version)
    return sorted_versions(candidates)


def read_update_check_cache() -> dict[str, Any] | None:
    path = update_check_cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_update_check_cache(data: dict[str, Any]) -> None:
    path = update_check_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    except OSError:
        return


def update_check_cache_path() -> Path:
    override = os.environ.get("POPS_UPDATE_CHECK_CACHE")
    if override:
        return Path(override).expanduser()
    if sys.platform.startswith("win") and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    elif os.environ.get("XDG_CACHE_HOME"):
        base = Path(os.environ["XDG_CACHE_HOME"]).expanduser()
    else:
        base = Path.home() / ".cache"
    return base / "pops" / "update-check.json"


def as_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None
