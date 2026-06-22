"""Version parsing and comparison helpers."""

from __future__ import annotations

import importlib.metadata
from collections.abc import Iterator, Sequence

from paperops.cli.constants import PACKAGE_NAME


def package_version() -> str:
    try:
        from paperops import __version__

        return __version__
    except ImportError:
        return importlib.metadata.version(PACKAGE_NAME)


def is_newer_version(latest: str, current: str) -> bool:
    return compare_versions(latest, current) > 0


def compare_versions(left: str, right: str) -> int:
    left_release = release_version_tuple(left)
    right_release = release_version_tuple(right)
    if not left_release or not right_release:
        if left == right:
            return 0
        return 1 if left > right else -1
    width = max(len(left_release), len(right_release))
    left_padded = left_release + (0,) * (width - len(left_release))
    right_padded = right_release + (0,) * (width - len(right_release))
    if left_padded == right_padded:
        return 0
    return 1 if left_padded > right_padded else -1


def sorted_versions(versions: Sequence[str] | Iterator[str]) -> list[str]:
    unique = {version for version in versions if release_version_tuple(version)}
    return sorted(unique, key=release_version_tuple)


def major_version(version: str) -> int:
    release = release_version_tuple(version)
    return release[0] if release else 0


def minor_checkpoint(version: str) -> str:
    release = release_version_tuple(version)
    if len(release) >= 2:
        return f"{release[0]}.{release[1]}"
    if len(release) == 1:
        return f"{release[0]}.0"
    return "0.0"


def release_version_tuple(version: str) -> tuple[int, ...]:
    release = version.split("+", 1)[0].split("-", 1)[0]
    parts: list[int] = []
    for raw in release.split("."):
        digits = ""
        for char in raw:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)
