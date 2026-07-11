"""CLI command handlers for paperops scaffold migrations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperops.cli.manifest import (
    applied_migrations,
    record_applied_migration,
    write_manifest,
)
from paperops.cli.migrations import (
    apply_migration,
    find_migration_root,
    get_migration,
    plan_migration,
    registered_migrations,
)


def add_migrate_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    migrate_parser = subcommands.add_parser(
        "migrate",
        help="Adopt or migrate an existing scaffold project.",
    )
    migrate_parser.add_argument(
        "migrate_args",
        nargs=argparse.REMAINDER,
        help=(
            "Use `list`, `show <id>`, or `apply <id> [path]`. Without a "
            "subcommand, keeps the legacy .pops adoption behavior."
        ),
    )
    migrate_parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing .pops metadata.",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show migration writes without changing files.",
    )
    migrate_parser.set_defaults(func=cmd_migrate)
    return migrate_parser


def cmd_migrate(args: argparse.Namespace) -> int:
    tokens = list(args.migrate_args)
    dry_run = args.dry_run or "--dry-run" in tokens
    legacy_apply = args.apply or "--apply" in tokens
    tokens = [token for token in tokens if token not in {"--dry-run", "--apply"}]
    if tokens and tokens[0] == "list":
        return cmd_migrate_list()
    if tokens and tokens[0] == "show":
        if len(tokens) < 2:
            print("error: migrate show requires a migration id.", file=sys.stderr)
            return 2
        return cmd_migrate_show(tokens[1])
    if tokens and tokens[0] == "apply":
        if len(tokens) < 2:
            print("error: migrate apply requires a migration id.", file=sys.stderr)
            return 2
        path = Path(tokens[2]) if len(tokens) >= 3 else Path.cwd()
        return cmd_migrate_apply(tokens[1], path, dry_run=dry_run)

    legacy_path = Path(tokens[0]) if tokens else Path.cwd()
    root = find_migration_root(legacy_path)
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    args.project_root = root
    manifest = root / ".pops" / "manifest.toml"
    legacy_paths = [
        "docs/project-brief.md",
        "docs/target-venue.md",
        "docs/contribution-claims.md",
        "docs/terminology-ja-en.md",
    ]
    present_legacy = [path for path in legacy_paths if (root / path).exists()]

    if manifest.exists():
        print(".pops/manifest.toml already exists.")
    elif legacy_apply:
        write_manifest(root)
        print("Created .pops/manifest.toml")
    else:
        print("Would create .pops/manifest.toml")

    if present_legacy:
        print("Legacy paths to review manually:")
        for path in present_legacy:
            print(f"  {path}")
    else:
        print("No known legacy docs paths found.")
    return 0


def cmd_migrate_list() -> int:
    print("Registered paperops migrations:")
    for migration in registered_migrations():
        print(f"- {migration.migration_id}: {migration.title} ({migration.checkpoint})")
    return 0


def cmd_migrate_show(migration_id: str) -> int:
    migration = get_migration(migration_id)
    if migration is None:
        print(f"error: unknown migration: {migration_id}", file=sys.stderr)
        return 2
    print(f"# {migration.migration_id}: {migration.title}")
    print("")
    print(f"- checkpoint: {migration.checkpoint}")
    print(f"- summary: {migration.summary}")
    print("")
    print("Moves:")
    if migration.moves:
        for source, target in migration.moves:
            print(f"- {source} -> {target}")
    else:
        print("- none")
    if migration.notes:
        print("")
        print("Notes:")
        for note in migration.notes:
            print(f"- {note}")
    return 0


def cmd_migrate_apply(migration_id: str, path: Path, *, dry_run: bool) -> int:
    migration = get_migration(migration_id)
    if migration is None:
        print(f"error: unknown migration: {migration_id}", file=sys.stderr)
        return 2
    root = find_migration_root(path)
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    if migration.migration_id in applied_migrations(root):
        print(f"Migration {migration.migration_id} is already applied; no changes made.")
        return 0

    plan = plan_migration(root, migration)
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"{mode} migration {migration.migration_id}: {migration.title}")
    print(f"Project root: {root}")
    if plan.moves:
        print("Planned moves:")
        for source, target in plan.moves:
            print(f"- {source} -> {target}")
    else:
        print("No file moves are planned.")
        for note in migration.notes:
            print(f"- {note}")

    if plan.conflicts:
        print("Migration conflict: target path already exists for these sources:", file=sys.stderr)
        for source, target in plan.conflicts:
            print(f"- {source} -> {target}", file=sys.stderr)
        print("No files were moved. Resolve or archive the legacy paths, then rerun.", file=sys.stderr)
        return 1

    apply_migration(root, plan, dry_run=dry_run)
    if dry_run:
        return 0
    if not (root / ".pops" / "manifest.toml").exists():
        write_manifest(root)
        print("Created .pops/manifest.toml")
    record_applied_migration(root, migration.migration_id)
    print(f"Applied migration {migration.migration_id}")
    return 0
