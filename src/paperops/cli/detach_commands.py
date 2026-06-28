"""CLI command handlers for detached managed scaffold files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperops.cli.manifest import (
    detached_records,
    record_detached_file,
    remove_detached_file,
    write_manifest,
)
from paperops.cli.project import find_project_root
from paperops.cli.scaffold import is_managed_update


def add_detach_parsers(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    detach_parser = subcommands.add_parser(
        "detach",
        help="Mark a managed paperops file as a project fork.",
    )
    detach_parser.add_argument(
        "managed_path",
        nargs="?",
        help="Use `<managed-path> [project]` or `list [project]`.",
    )
    detach_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    detach_parser.add_argument(
        "--reason",
        default="",
        help="Why this managed file is intentionally forked.",
    )
    detach_parser.set_defaults(func=cmd_detach)

    reattach_parser = subcommands.add_parser(
        "reattach",
        help="Remove a managed paperops file from the detached fork manifest.",
    )
    reattach_parser.add_argument("managed_path", help="Managed file path.")
    reattach_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    reattach_parser.set_defaults(func=cmd_reattach)


def cmd_detach(args: argparse.Namespace) -> int:
    if args.managed_path == "list":
        path = args.path or Path.cwd()
        root = find_project_root(path)
        if root is None:
            print("error: this does not look like a paper harness project.", file=sys.stderr)
            return 2
        records = detached_records(root)
        if not records:
            print("Detached managed files: none")
            return 0
        print("Detached managed files:")
        for rel, record in sorted(records.items()):
            reason = record.get("reason", "")
            suffix = f" -- {reason}" if reason else ""
            print(f"- {rel}{suffix}")
        return 0

    if not args.managed_path:
        print("error: detach requires a managed file path or `list`.", file=sys.stderr)
        return 2
    rel = args.managed_path.strip().strip("/").replace("\\", "/")
    path = args.path or Path.cwd()
    reason = args.reason.strip()
    if not reason:
        print("error: detach requires --reason.", file=sys.stderr)
        return 2
    root = find_project_root(path)
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2
    if not is_managed_update(rel):
        print(f"error: not a managed paperops file: {rel}", file=sys.stderr)
        return 2
    if not (root / rel).is_file():
        print(f"error: managed file is missing: {rel}", file=sys.stderr)
        return 2
    if not (root / ".pops" / "manifest.toml").exists():
        write_manifest(root)
    record_detached_file(root, rel, reason=reason)
    print(f"Detached managed file: {rel}")
    print("Future update-paperops runs will report it as a detached fork.")
    return 0


def cmd_reattach(args: argparse.Namespace) -> int:
    rel = args.managed_path.strip().strip("/").replace("\\", "/")
    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2
    if not is_managed_update(rel):
        print(f"error: not a managed paperops file: {rel}", file=sys.stderr)
        return 2
    removed = remove_detached_file(root, rel)
    if removed:
        print(f"Reattached managed file: {rel}")
        print("Future update-paperops runs will include it in managed update plans.")
    else:
        print(f"Managed file is already attached: {rel}")
    return 0
