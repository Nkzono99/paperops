"""Versioned upgrade-chain planning and execution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from paperops.cli.constants import PACKAGE_NAME
from paperops.cli.models import UpgradeStep
from paperops.cli.versioning import (
    compare_versions,
    minor_checkpoint,
    release_version_tuple,
    sorted_versions,
)


def resolve_upgrade_target(target: str, versions: list[str]) -> str | None:
    if not versions:
        return None
    if target == "latest":
        return versions[-1]
    if target in versions:
        return target
    target_release = release_version_tuple(target)
    if not target_release:
        return None
    matches = [
        version
        for version in versions
        if release_version_tuple(version)[: len(target_release)] == target_release
    ]
    return matches[-1] if matches else None


def plan_upgrade_chain(
    applied: str,
    target: str,
    versions: list[str],
) -> list[UpgradeStep]:
    if compare_versions(target, applied) <= 0:
        return []

    candidates = [
        version
        for version in sorted_versions([*versions, target])
        if compare_versions(version, applied) > 0
        and compare_versions(version, target) <= 0
    ]
    by_minor: dict[str, str] = {}
    applied_minor = minor_checkpoint(applied)
    target_minor = minor_checkpoint(target)
    for version in candidates:
        checkpoint = minor_checkpoint(version)
        if checkpoint == applied_minor and checkpoint != target_minor:
            continue
        by_minor[checkpoint] = version

    steps: list[UpgradeStep] = []
    current = applied
    for checkpoint in sorted_versions(list(by_minor.values())):
        if compare_versions(checkpoint, current) > 0:
            steps.append(UpgradeStep(from_version=current, to_version=checkpoint))
            current = checkpoint
    return steps


def print_upgrade_chain(applied: str, target: str, chain: list[UpgradeStep]) -> None:
    print("Paperops upgrade chain:")
    print(f"  current repo artifacts: {applied}")
    print(f"  target package:          {target}")
    if not chain:
        print("  status: already up to date")
        return
    print("")
    print("planned upgrade chain:")
    for index, step in enumerate(chain, start=1):
        kind = "major" if step.is_major else "minor"
        print(f"{index}. {step.from_version} -> {step.to_version} ({kind})")


def run_upgrade_chain(root: Path, chain: list[UpgradeStep], *, force: bool) -> int:
    for step in chain:
        command = [
            "uvx",
            "--from",
            f"{PACKAGE_NAME}=={step.to_version}",
            "pops",
            "update-paperops",
            "--upgrade-step",
            "--from-version",
            step.from_version,
            "--to-version",
            step.to_version,
            "--apply",
        ]
        if force:
            command.append("--force")
        print("Running: " + " ".join(command))
        try:
            result = subprocess.run(command, cwd=root, check=False)
        except OSError as exc:
            print(f"error: failed to run upgrade step: {exc}", file=sys.stderr)
            return 1
        if result.returncode != 0:
            print(
                f"error: upgrade step failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            return result.returncode
    return 0
