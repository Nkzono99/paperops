"""User-facing deprecation and version update notices."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from paperops.cli.constants import CHANGELOG_URL
from paperops.cli.manifest import applied_scaffold_version
from paperops.cli.project import find_project_root
from paperops.cli.pypi import latest_package_version
from paperops.cli.runtime import uvx_pops_command
from paperops.cli.versioning import is_newer_version, package_version


def maybe_print_update_notice(args: argparse.Namespace, exit_code: int) -> None:
    if exit_code != 0 or args.command == "version":
        return
    if env_truthy("POPS_DISABLE_VERSION_CHECK"):
        return
    if not (sys.stderr.isatty() or env_truthy("POPS_FORCE_VERSION_CHECK")):
        return

    current = package_version()
    project_root = getattr(args, "project_root", None)
    if not isinstance(project_root, Path):
        project_root = find_project_root(Path.cwd())
    applied = applied_scaffold_version(project_root) if project_root is not None else None
    latest = latest_package_version()
    update_target = current
    printed = False
    latest_is_newer = latest is not None and is_newer_version(latest, current)

    if latest is not None and latest_is_newer:
        update_target = latest
        print(
            f"[pops notice] 実行中の pops が古いです: {current} -> {latest}",
            file=sys.stderr,
        )
        print(
            f"[pops notice] 標準実行: {uvx_pops_command('<command>')}",
            file=sys.stderr,
        )
        if applied is None:
            print(
                "[pops notice] 論文プロジェクト内では "
                f"{uvx_pops_command('update-paperops', '--plan')} "
                "で upgrade chain を確認してください。",
                file=sys.stderr,
            )
            print(
                "[pops notice] 反映は agent に /update-paperops "
                "（未導入なら /pull-template-updates）で依頼してください。",
                file=sys.stderr,
            )
        printed = True

    if applied is not None and is_newer_version(applied, current):
        print(
            "[pops notice] 実行中の pops がこのプロジェクトの適用済み "
            f"scaffold より古いです: {current} -> {applied}",
            file=sys.stderr,
        )
        if not latest_is_newer:
            print(
                f"[pops notice] 標準実行: {uvx_pops_command('<command>')}",
                file=sys.stderr,
            )
        printed = True

    if applied is not None and is_newer_version(update_target, applied):
        print(
            "[pops notice] このプロジェクトの paperops ハーネス更新候補: "
            f"{applied} -> {update_target}",
            file=sys.stderr,
        )
        print(
            f"[pops notice] chain確認: {uvx_pops_command('update-paperops', '--plan')}",
            file=sys.stderr,
        )
        print(
            "[pops notice] 反映は agent に /update-paperops "
            "（未導入なら /pull-template-updates）で依頼してください。",
            file=sys.stderr,
        )
        printed = True

    if not printed:
        return

    print(f"[pops notice] 更新内容: {CHANGELOG_URL}", file=sys.stderr)
    print(
        "[pops notice] この確認を止めるには POPS_DISABLE_VERSION_CHECK=1 を設定します。",
        file=sys.stderr,
    )


def env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def warn_ignored_bootstrap_options(args: argparse.Namespace) -> None:
    if not (
        getattr(args, "skip_venv", False)
        or getattr(args, "skip_install", False)
        or getattr(args, "install_spec", "")
    ):
        return
    print(
        "[pops notice] project-local pops bootstrap options are deprecated; "
        f"use {uvx_pops_command('<command>')} for CLI commands.",
        file=sys.stderr,
    )
