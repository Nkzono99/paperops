"""Minimal ``pops`` CLI for paper harness projects."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from paperops.authority_bootstrap import bootstrap_v2_authority
from paperops.cli.constants import PACKAGE_NAME, UPSTREAM_REPO
from paperops.cli.compile_commands import add_compile_parser
from paperops.cli.change_commands import add_change_parser
from paperops.cli.write_commands import add_write_parser
from paperops.cli.doctor import (
    check_executable,
    check_path,
    check_project_venv_if_present,
    check_uvx_available,
    check_workflow_placeholders,
    print_manual_setup_hints,
)
from paperops.cli.detach_commands import add_detach_parsers
from paperops.cli.links import iter_links, validate_link_registry
from paperops.cli.manifest import (
    applied_scaffold_version,
    write_cli_metadata,
    write_manifest,
)
from paperops.cli.migration_commands import add_migrate_parser
from paperops.cli.models import CopyPlan
from paperops.cli.model_commands import add_model_parser
from paperops.cli.notices import maybe_print_update_notice, warn_ignored_bootstrap_options
from paperops.cli.output import print_copy_summary, print_next_steps, print_update_plan
from paperops.cli.paths import internal_file
from paperops.cli.project import (
    detect_template_ref,
    find_project_root,
    resolve_setup_target,
)
from paperops.cli.pypi import available_package_versions
from paperops.cli.scaffold import (
    apply_managed_update,
    copy_scaffold,
    parse_only,
    plan_managed_update,
    scaffold_source,
    source_dir_context,
)
from paperops.cli.scratch import add_scratch_parser
from paperops.cli.upgrade import (
    plan_upgrade_chain,
    print_upgrade_chain,
    resolve_upgrade_target,
    run_upgrade_chain,
)
from paperops.cli.versioning import compare_versions, package_version
from paperops.cli.workflow import add_workflow_parser


def app() -> None:
    """Console-script entrypoint."""

    raise SystemExit(main())


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        return cmd_version(args)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    code = args.func(args)
    if getattr(args, "command", "") not in {"compile", "write", "workflow"}:
        maybe_print_update_notice(args, code)
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pops",
        description="Paper harness project operations.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print CLI and scaffold version information.",
    )
    subcommands = parser.add_subparsers(dest="command")

    init_parser = subcommands.add_parser("init", help="Create a paper project.")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Copy into an existing directory without overwriting files.",
    )
    init_parser.add_argument(
        "--template-ref",
        default="",
        help="Optional upstream template ref to record in .pops/manifest.toml.",
    )
    init_parser.add_argument(
        "--skip-venv",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    init_parser.add_argument(
        "--skip-install",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    init_parser.add_argument(
        "--install-spec",
        default="",
        help=argparse.SUPPRESS,
    )
    init_parser.set_defaults(func=cmd_init)

    setup_parser = subcommands.add_parser(
        "setup",
        help="Prepare a local paper project.",
    )
    setup_parser.add_argument("url", nargs="?", help="Optional Git URL to clone before setup.")
    setup_parser.add_argument(
        "--path",
        "-p",
        type=Path,
        help="Destination or existing project directory.",
    )
    setup_parser.add_argument(
        "--skip-venv",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    setup_parser.add_argument(
        "--skip-install",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    setup_parser.add_argument(
        "--install-spec",
        default="",
        help=argparse.SUPPRESS,
    )
    setup_parser.set_defaults(func=cmd_setup)

    doctor_parser = subcommands.add_parser("doctor", help="Check local project health.")
    doctor_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Project directory, defaults to cwd.",
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    add_update_paperops_parser(
        subcommands,
        "update-paperops",
        "Plan or apply managed paperops updates.",
    )
    add_update_paperops_parser(
        subcommands,
        "update-harness",
        "Backward-compatible alias for update-paperops.",
    )

    add_migrate_parser(subcommands)
    add_model_parser(subcommands)
    add_change_parser(subcommands)
    add_compile_parser(subcommands)
    add_write_parser(subcommands)

    feedback_parser = subcommands.add_parser(
        "feedback",
        help="Draft upstream template feedback.",
    )
    feedback_parser.add_argument(
        "--kind",
        choices=("template-feedback", "skill-request", "structure-change"),
        default="template-feedback",
    )
    feedback_parser.add_argument("--title", default="")
    feedback_parser.add_argument("--body", default="")
    feedback_parser.add_argument("--output", type=Path, help="Write the draft to this file.")
    feedback_parser.add_argument("--repo", default=UPSTREAM_REPO)
    feedback_parser.set_defaults(func=cmd_feedback)

    links_parser = subcommands.add_parser(
        "links",
        help="Inspect paper draft links to external projects and directories.",
    )
    links_parser.add_argument(
        "action",
        choices=("list", "check"),
        help="List links or validate the link registry.",
    )
    links_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Project directory, defaults to cwd.",
    )
    links_parser.add_argument(
        "--resolve-local",
        action="store_true",
        help="Show local paths from _paperops/refs/local/locations.toml when listing.",
    )
    links_parser.add_argument(
        "--strict-local",
        action="store_true",
        help="Warn when _paperops/refs/local/locations.toml is missing.",
    )
    links_parser.set_defaults(func=cmd_links)

    add_detach_parsers(subcommands)

    add_workflow_parser(subcommands)
    add_scratch_parser(subcommands)

    version_parser = subcommands.add_parser(
        "version",
        help="Print CLI and scaffold version information.",
    )
    version_parser.set_defaults(func=cmd_version)

    return parser


def add_update_paperops_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    update_parser = subcommands.add_parser(name, help=help_text)
    update_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Project directory, defaults to cwd.",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the plan without writing.",
    )
    update_parser.add_argument(
        "--plan",
        action="store_true",
        help="Show a versioned upgrade chain without writing.",
    )
    update_parser.add_argument("--apply", action="store_true", help="Apply missing-file updates.")
    update_parser.add_argument(
        "--apply-chain",
        action="store_true",
        help="Run a versioned upgrade chain via exact uvx package versions.",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite changed managed files when used with --apply.",
    )
    update_parser.add_argument(
        "--target",
        default="latest",
        help="Upgrade chain target version or minor prefix, defaults to latest.",
    )
    update_parser.add_argument(
        "--allow-major",
        action="store_true",
        help="Allow --apply-chain to cross a major version boundary.",
    )
    update_parser.add_argument(
        "--upgrade-step",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    update_parser.add_argument("--from-version", default="", help=argparse.SUPPRESS)
    update_parser.add_argument("--to-version", default="", help=argparse.SUPPRESS)
    update_parser.add_argument(
        "--adopt",
        action="store_true",
        help="Create or refresh .pops/manifest.toml without copying files.",
    )
    update_parser.add_argument("--only", help="Comma-separated path prefixes to consider.")
    update_parser.add_argument(
        "--source",
        type=Path,
        help="Use a scaffold directory instead of the bundled scaffold.",
    )
    update_parser.add_argument(
        "--template-ref",
        default="",
        help="Template commit/ref to record in .pops/manifest.toml.",
    )
    update_parser.set_defaults(func=cmd_update_paperops)
    return update_parser


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(os.path.abspath(Path(args.path).expanduser()))
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        print(
            "error: target must be a directory path, not a symlink or "
            f"special file: {target}",
            file=sys.stderr,
        )
        return 2
    nonempty = target.is_dir() and any(target.iterdir())
    if nonempty and not args.force:
        print(f"error: target is not empty: {target}", file=sys.stderr)
        print(
            "hint: choose a new directory or pass --force to copy only missing files.",
            file=sys.stderr,
        )
        return 2
    if nonempty:
        print(
            "error: v2 authority cannot be claimed while force-copying into "
            "a non-empty target.",
            file=sys.stderr,
        )
        print(
            "hint: use pops setup/update-paperops, then migrate the existing project explicitly.",
            file=sys.stderr,
        )
        return 2

    try:
        plan, hashes = _initialize_staged_project(
            target,
            template_ref=args.template_ref,
        )
    except ValueError as error:
        print(f"error: initialization failed: {error}", file=sys.stderr)
        return 1
    except OSError:
        print(
            f"error: initialization failed: target could not be installed safely: {target}",
            file=sys.stderr,
        )
        return 1

    args.project_root = target
    print(f"Initialized paper project: {target}")
    print_copy_summary(plan)
    print("Authority: v2-authoritative")
    print("Workflow: v2-authoritative")
    print("Model hashes:")
    for name, digest in hashes.items():
        print(f"  {name}: {digest}")
    warn_ignored_bootstrap_options(args)

    print_next_steps(target)
    return 0


def _initialize_staged_project(
    target: Path,
    *,
    template_ref: str,
) -> tuple[CopyPlan, dict[str, str]]:
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(target):
        if target.is_symlink() or not target.is_dir() or any(target.iterdir()):
            raise FileExistsError(f"target is no longer an empty directory: {target}")
        restore_empty = True
        restore_mode = stat.S_IMODE(target.stat().st_mode)
    else:
        restore_empty = False
        restore_mode = 0
    staging: Path | None = None
    reservation_created = False
    reservation_locked = False
    reservation_identity: tuple[int, int] | None = None
    installed = False
    try:
        if restore_empty:
            staging = Path(
                tempfile.mkdtemp(prefix=f".{target.name}.pops-init-", dir=target.parent)
            )
            shutil.copystat(target, staging, follow_symlinks=False)
            reserved = target.stat()
            reservation_identity = (reserved.st_dev, reserved.st_ino)
            target.chmod(0o500)
            reservation_locked = True
        else:
            previous_umask = os.umask(0)
            os.umask(previous_umask)
            target.mkdir(mode=0o500)
            reservation_created = True
            reserved = target.stat()
            reservation_identity = (reserved.st_dev, reserved.st_ino)
            target.chmod(0o500)
            staging = Path(
                tempfile.mkdtemp(prefix=f".{target.name}.pops-init-", dir=target.parent)
            )
            staging.chmod(0o777 & ~previous_umask)
        if any(target.iterdir()):
            raise FileExistsError(f"target changed while initialization was starting: {target}")
        with scaffold_source() as source:
            plan = copy_scaffold(source, staging, overwrite=False)
        write_manifest(staging, template_ref=template_ref)
        hashes = bootstrap_v2_authority(staging)
        if not _is_empty_reservation(target, reservation_identity):
            raise FileExistsError(f"target changed during initialization: {target}")
        os.replace(staging, target)
        installed = True
        return plan, hashes
    finally:
        if not installed:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            if _is_empty_reservation(target, reservation_identity):
                if reservation_created:
                    target.rmdir()
                elif reservation_locked:
                    target.chmod(restore_mode)


def _is_empty_reservation(
    target: Path,
    identity: tuple[int, int] | None,
) -> bool:
    if identity is None:
        return False
    try:
        metadata = target.stat()
        return (
            target.is_dir()
            and (metadata.st_dev, metadata.st_ino) == identity
            and not any(target.iterdir())
        )
    except OSError:
        return False


def cmd_setup(args: argparse.Namespace) -> int:
    start = resolve_setup_target(args.url, args.path)
    root = find_project_root(start)
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    print(f"Project root: {root}")
    args.project_root = root
    if not (root / ".pops" / "manifest.toml").exists():
        write_manifest(root)
        print("Created .pops/manifest.toml")
    else:
        write_cli_metadata(root)
        print("Updated .pops CLI runner metadata")

    warn_ignored_bootstrap_options(args)

    print_manual_setup_hints(root)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = find_project_root(args.path or Path.cwd())
    errors: list[str] = []
    warnings: list[str] = []

    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    args.project_root = root
    print(f"Project root: {root}")
    print(f"Python: {sys.version.split()[0]}")
    check_path(root, "Makefile", errors)
    check_path(root, "manuscript", errors)
    check_path(root, "_paperops", errors)
    check_path(root, "story", warnings)
    check_path(root, "scripts", errors)
    check_path(root, ".pops/manifest.toml", warnings)
    check_uvx_available(warnings)
    check_project_venv_if_present(root, warnings)
    check_executable("git", warnings)
    check_executable("make", warnings)
    check_workflow_placeholders(root, warnings)
    for finding in validate_link_registry(root):
        if finding.severity == "error":
            errors.append(finding.message)
        else:
            warnings.append(finding.message)

    local_locations = internal_file(root, "refs/local/locations.toml")
    if not local_locations.exists():
        warnings.append(
            "_paperops/refs/local/locations.toml is missing; copy "
            "_paperops/refs/local/locations.example.toml when local paths are needed."
        )

    for item in errors:
        print(f"[error] {item}")
    for item in warnings:
        print(f"[warn] {item}")
    if errors:
        print("doctor: failed")
        return 1
    print("doctor: ok")
    print(
        "doctor scope: structure and local setup only; run "
        "make readiness-check before sharing or submission."
    )
    print(
        "Skill context budget warning: if Codex says skill descriptions were shortened, "
        "see TROUBLESHOOTING.md and keep only the plugins needed for the current profile."
    )
    return 0


def cmd_update_paperops(args: argparse.Namespace) -> int:
    if args.apply and args.dry_run:
        print("error: --apply and --dry-run cannot be used together.", file=sys.stderr)
        return 2
    if args.apply_chain and (args.apply or args.dry_run):
        print(
            "error: --apply-chain cannot be combined with --apply or --dry-run.",
            file=sys.stderr,
        )
        return 2

    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    args.project_root = root
    if args.upgrade_step:
        return cmd_upgrade_step(args, root)

    if args.plan or args.apply_chain:
        return cmd_upgrade_chain(args, root)

    if args.adopt:
        template_ref = args.template_ref or detect_template_ref(args.source)
        write_manifest(root, template_ref=template_ref)
        print("Adopted current project into .pops/manifest.toml")
        return 0

    source_context = source_dir_context(args.source)
    with source_context as source:
        template_ref = args.template_ref or detect_template_ref(source)
        only = parse_only(args.only)
        plan = plan_managed_update(source, root, only_prefixes=only)
        print_update_plan(plan)
        if args.apply:
            if plan.changed and not args.force:
                print(
                    "error: changed managed files block this update. "
                    "Review the plan, detach intentional forks, or re-run with "
                    "--apply --force only when local edits may be replaced.",
                    file=sys.stderr,
                )
                return 1
            applied = apply_managed_update(
                source,
                root,
                plan,
                overwrite=args.force,
                template_ref=template_ref,
            )
            print(f"Applied files: {applied}")
    return 0


def cmd_upgrade_chain(args: argparse.Namespace, root: Path) -> int:
    applied = applied_scaffold_version(root) or package_version()
    versions = available_package_versions()
    if not versions:
        print("error: could not resolve available paperops versions.", file=sys.stderr)
        return 1

    target = resolve_upgrade_target(args.target, versions)
    if target is None:
        print(f"error: target version was not found: {args.target}", file=sys.stderr)
        return 2

    chain = plan_upgrade_chain(applied, target, versions)
    print_upgrade_chain(applied, target, chain)
    if not chain:
        return 0

    if args.apply_chain and any(step.is_major for step in chain) and not args.allow_major:
        print(
            "error: upgrade chain crosses a major version; re-run with --allow-major "
            "after reviewing the plan.",
            file=sys.stderr,
        )
        return 2

    if args.apply_chain:
        return run_upgrade_chain(root, chain, force=args.force)

    return 0


def cmd_upgrade_step(args: argparse.Namespace, root: Path) -> int:
    if not args.from_version or not args.to_version:
        print(
            "error: --upgrade-step requires --from-version and --to-version.",
            file=sys.stderr,
        )
        return 2

    applied = applied_scaffold_version(root)
    if applied is not None and compare_versions(applied, args.from_version) != 0:
        print(
            "error: upgrade step expected scaffold "
            f"{args.from_version}, but manifest records {applied}.",
            file=sys.stderr,
        )
        return 2

    source_context = source_dir_context(args.source)
    with source_context as source:
        template_ref = args.template_ref or f"{PACKAGE_NAME}=={package_version()}"
        only = parse_only(args.only)
        plan = plan_managed_update(source, root, only_prefixes=only)
        print(
            f"Paperops upgrade step: {args.from_version} -> {args.to_version}"
        )
        print_update_plan(plan)
        if args.apply:
            if plan.changed and not args.force:
                print(
                    "error: changed managed files block this upgrade step. "
                    "Review the plan, detach intentional forks, or re-run this step "
                    "with --force only when local edits may be replaced.",
                    file=sys.stderr,
                )
                return 1
            applied_count = apply_managed_update(
                source,
                root,
                plan,
                overwrite=args.force,
                template_ref=template_ref,
            )
            write_manifest(root, template_ref=template_ref)
            print(f"Applied files: {applied_count}")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    root = find_project_root(Path.cwd()) or Path.cwd()
    title = args.title or "テンプレート改善フィードバック"
    body = args.body or "背景、再現手順、期待する改善を記入してください。"
    content = "\n".join(
        [
            f"# {title}",
            "",
            f"- kind: `{args.kind}`",
            f"- upstream: `{args.repo}`",
            f"- project: `{root}`",
            "",
            "## 背景",
            "",
            body,
            "",
            "## 期待する変更",
            "",
            "- ",
            "",
            "## 下流互換性メモ",
            "",
            "- ",
            "",
        ]
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"Wrote feedback draft: {args.output}")
    else:
        print(content)
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    args.project_root = root
    if args.action == "check":
        findings = validate_link_registry(root, strict_local=args.strict_local)
        errors = [finding for finding in findings if finding.severity == "error"]
        warnings = [finding for finding in findings if finding.severity != "error"]
        print(f"Project root: {root}")
        for item in errors:
            print(f"[error] {item.message}")
        for item in warnings:
            print(f"[warn] {item.message}")
        if errors:
            print("links: failed")
            return 1
        print("links: ok")
        return 0

    findings = validate_link_registry(root)
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        print(f"Project root: {root}")
        for item in errors:
            print(f"[error] {item.message}")
        print("links: failed")
        return 1

    rows = iter_links(root, resolve_local=args.resolve_local)
    print(f"Project root: {root}")
    if not rows:
        print("No links registered.")
        return 0
    print("Paper links:")
    for row in rows:
        link_id = str(row.get("id", ""))
        kind = str(row.get("kind", ""))
        location_ref = str(row.get("location_ref", ""))
        role_values = row.get("paper_roles", [])
        roles = ", ".join(str(role) for role in role_values) if isinstance(role_values, list) else ""
        description = str(row.get("description", ""))
        suffix = f" roles=[{roles}]" if roles else ""
        print(f"- {link_id} ({kind}) -> {location_ref}{suffix}")
        if description:
            print(f"  {description}")
        mcp_provider = str(row.get("mcp_provider", "")).strip()
        mcp_server = str(row.get("mcp_server", "")).strip()
        if mcp_provider or mcp_server:
            server_text = f"/{mcp_server}" if mcp_server else ""
            print(f"  mcp: {mcp_provider}{server_text}")
        paper_request_queue = str(row.get("paper_request_queue", "")).strip()
        if paper_request_queue:
            print(f"  paper requests: {paper_request_queue}")
        tool_values = row.get("mcp_tools", [])
        if isinstance(tool_values, list):
            request_tools = [
                str(tool).strip()
                for tool in tool_values
                if str(tool).strip().startswith("runops.paper.")
            ]
            if request_tools:
                print(f"  paper request tools: {', '.join(request_tools)}")
        if args.resolve_local and row.get("local_path"):
            host = str(row.get("local_host", ""))
            host_text = f" [{host}]" if host else ""
            print(f"  local: {row['local_path']}{host_text}")
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"pops {package_version()}")
    print(f"package {PACKAGE_NAME}")
    print(f"upstream {UPSTREAM_REPO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
