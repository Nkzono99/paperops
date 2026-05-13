"""Small data models shared by CLI modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CopyPlan:
    missing: list[str]
    changed: list[str]
    unchanged: list[str]
    excluded: list[str]


@dataclass(frozen=True)
class UpgradeStep:
    from_version: str
    to_version: str

    @property
    def is_major(self) -> bool:
        from paperops.cli.versioning import major_version

        return major_version(self.from_version) != major_version(self.to_version)
