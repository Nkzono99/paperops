"""Minimal ``pops`` CLI for paper harness projects."""

from __future__ import annotations

import argparse
import fnmatch
import importlib.metadata
import importlib.resources
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PACKAGE_NAME = "paper-harness-cli"
UPSTREAM_REPO = "Nkzono99/paperops"
CHANGELOG_URL = f"https://github.com/{UPSTREAM_REPO}/blob/main/CHANGELOG.md"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60

EXCLUDED_SCAFFOLD_PATTERNS = (
    ".git",
    ".git/*",
    ".venv",
    ".venv/*",
    "dist",
    "dist/*",
    ".claude/settings.local.json",
    "notes/session-context.generated.md",
    "manuscript/mirror/reports/latest.md",
    "manuscript/mirror/reports/smoke-check.md",
    "manuscript/shared/build/en",
    "manuscript/shared/build/en/*",
    "manuscript/shared/build/ja",
    "manuscript/shared/build/ja/*",
    "refs/local/locations.toml",
)

MANAGED_UPDATE_PATTERNS = (
    "AGENTS.md",
    "CLAUDE.md",
    "Makefile",
    "TROUBLESHOOTING.md",
    "scripts/*",
    ".agents/*",
    ".claude/*",
    ".github/ISSUE_TEMPLATE/*",
    ".github/PULL_REQUEST_TEMPLATE.md",
)

PROJECT_MARKERS = (
    "manuscript",
    "notes",
    "scripts",
    "Makefile",
)


@dataclass(frozen=True)
class CopyPlan:
    missing: list[str]
    changed: list[str]
    unchanged: list[str]
    excluded: list[str]


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
        help="Do not create .venv or install project-local pops.",
    )
    init_parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Create .venv but do not install project-local pops.",
    )
    init_parser.add_argument(
        "--install-spec",
        default="",
        help="Package spec to install into .venv, defaults to paper-harness-cli==version.",
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
    setup_parser.add_argument("--skip-venv", action="store_true", help="Do not create .venv.")
    setup_parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Do not install project-local pops into .venv.",
    )
    setup_parser.add_argument(
        "--install-spec",
        default="",
        help="Package spec to install into .venv, defaults to paper-harness-cli==version.",
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

    migrate_parser = subcommands.add_parser(
        "migrate",
        help="Adopt or migrate an existing scaffold project.",
    )
    migrate_parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="Project directory, defaults to cwd.",
    )
    migrate_parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing .pops metadata.",
    )
    migrate_parser.set_defaults(func=cmd_migrate)

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
    update_parser.add_argument("--apply", action="store_true", help="Apply missing-file updates.")
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite changed managed files when used with --apply.",
    )
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
    target = Path(args.path).expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        print(f"error: target is not empty: {target}", file=sys.stderr)
        print(
            "hint: choose a new directory or pass --force to copy only missing files.",
            file=sys.stderr,
        )
        return 2

    target.mkdir(parents=True, exist_ok=True)
    with scaffold_source() as source:
        plan = copy_scaffold(source, target, overwrite=False)

    write_manifest(target, template_ref=args.template_ref)
    print(f"Initialized paper project: {target}")
    print_copy_summary(plan)

    bootstrapped = bootstrap_project(
        target,
        skip_venv=args.skip_venv,
        skip_install=args.skip_install,
        install_spec=args.install_spec,
    )
    if not bootstrapped:
        return 1

    print_next_steps(target)
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    start = resolve_setup_target(args.url, args.path)
    root = find_project_root(start)
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    print(f"Project root: {root}")
    if not (root / ".pops" / "manifest.toml").exists():
        write_manifest(root)
        print("Created .pops/manifest.toml")

    bootstrapped = bootstrap_project(
        root,
        skip_venv=args.skip_venv,
        skip_install=args.skip_install,
        install_spec=args.install_spec,
    )
    if not bootstrapped:
        return 1

    print_manual_setup_hints(root)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = find_project_root(args.path or Path.cwd())
    errors: list[str] = []
    warnings: list[str] = []

    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    print(f"Project root: {root}")
    print(f"Python: {sys.version.split()[0]}")
    check_path(root, "Makefile", errors)
    check_path(root, "manuscript", errors)
    check_path(root, "notes", errors)
    check_path(root, "scripts", errors)
    check_path(root, ".pops/manifest.toml", warnings)
    check_project_local_cli(root, warnings)
    check_executable("git", warnings)
    check_executable("make", warnings)
    check_workflow_placeholders(root, warnings)

    local_locations = root / "refs" / "local" / "locations.toml"
    if not local_locations.exists():
        warnings.append(
            "refs/local/locations.toml is missing; copy "
            "refs/local/locations.example.toml when local paths are needed."
        )

    for item in errors:
        print(f"[error] {item}")
    for item in warnings:
        print(f"[warn] {item}")
    if errors:
        print("doctor: failed")
        return 1
    print("doctor: ok")
    return 0


def cmd_update_paperops(args: argparse.Namespace) -> int:
    if args.apply and args.dry_run:
        print("error: --apply and --dry-run cannot be used together.", file=sys.stderr)
        return 2

    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

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
            applied = apply_managed_update(
                source,
                root,
                plan,
                overwrite=args.force,
                template_ref=template_ref,
            )
            print(f"Applied files: {applied}")
            if plan.changed and not args.force:
                print(
                    "Changed managed files were left untouched. Re-run with "
                    "--apply --force only after reviewing the plan."
                )
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

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
    elif args.apply:
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


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"pops {package_version()}")
    print(f"package {PACKAGE_NAME}")
    print(f"upstream {UPSTREAM_REPO}")
    return 0


def package_version() -> str:
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        from paperops import __version__

        return __version__


def maybe_print_update_notice(args: argparse.Namespace, exit_code: int) -> None:
    if exit_code != 0 or args.command == "version":
        return
    if env_truthy("POPS_DISABLE_VERSION_CHECK"):
        return
    if not (sys.stderr.isatty() or env_truthy("POPS_FORCE_VERSION_CHECK")):
        return

    current = package_version()
    latest = latest_package_version()
    if latest is None or not is_newer_version(latest, current):
        return

    print(f"[pops notice] paperops の更新があります: {current} -> {latest}", file=sys.stderr)
    print(
        f"[pops notice] 更新内容: {CHANGELOG_URL}",
        file=sys.stderr,
    )
    print(
        f"[pops notice] CLI更新: uvx --from {PACKAGE_NAME} pops setup",
        file=sys.stderr,
    )
    print(
        "[pops notice] その後、agent に /update-paperops "
        "（未導入なら /pull-template-updates）で差分確認を依頼してください。",
        file=sys.stderr,
    )
    print(
        "[pops notice] この確認を止めるには POPS_DISABLE_VERSION_CHECK=1 を設定します。",
        file=sys.stderr,
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


def env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def as_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def is_newer_version(latest: str, current: str) -> bool:
    latest_release = release_version_tuple(latest)
    current_release = release_version_tuple(current)
    if not latest_release or not current_release:
        return latest != current and latest > current
    width = max(len(latest_release), len(current_release))
    return latest_release + (0,) * (width - len(latest_release)) > current_release + (
        0,
    ) * (width - len(current_release))


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


@contextmanager
def scaffold_source() -> Iterator[Path]:
    dev_source = Path(__file__).resolve().parents[3] / "template"
    if dev_source.is_dir():
        yield dev_source
        return

    package_source = importlib.resources.files("paperops") / "_data" / "scaffold"
    with importlib.resources.as_file(package_source) as source:
        yield source


@contextmanager
def source_dir_context(source: Path | None) -> Iterator[Path]:
    if source is not None:
        resolved = source.expanduser().resolve()
        if not resolved.is_dir():
            raise SystemExit(f"source directory not found: {resolved}")
        yield resolved
    else:
        with scaffold_source() as bundled:
            yield bundled


def copy_scaffold(source: Path, target: Path, *, overwrite: bool) -> CopyPlan:
    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    excluded: list[str] = []

    for src in sorted(source.rglob("*")):
        rel = normalize_rel(src.relative_to(source))
        if is_excluded(rel):
            excluded.append(rel)
            continue
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
            missing.append(rel)
        elif same_file_content(src, dst):
            unchanged.append(rel)
        elif overwrite:
            shutil.copy2(src, dst)
            changed.append(rel)
        else:
            changed.append(rel)
    return CopyPlan(missing=missing, changed=changed, unchanged=unchanged, excluded=excluded)


def plan_managed_update(
    source: Path,
    root: Path,
    *,
    only_prefixes: list[str] | None = None,
) -> CopyPlan:
    missing: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []
    excluded: list[str] = []
    for src in sorted(source.rglob("*")):
        rel = normalize_rel(src.relative_to(source))
        if src.is_dir():
            continue
        if (
            is_excluded(rel)
            or not is_managed_update(rel)
            or not path_requested(rel, only_prefixes)
        ):
            excluded.append(rel)
            continue
        dst = root / rel
        if not dst.exists():
            missing.append(rel)
        elif same_file_content(src, dst):
            unchanged.append(rel)
        else:
            changed.append(rel)
    return CopyPlan(missing=missing, changed=changed, unchanged=unchanged, excluded=excluded)


def apply_managed_update(
    source: Path,
    root: Path,
    plan: CopyPlan,
    *,
    overwrite: bool,
    template_ref: str = "",
) -> int:
    candidates = list(plan.missing)
    if overwrite:
        candidates.extend(plan.changed)

    for rel in candidates:
        src = source / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    if candidates:
        write_manifest(root, template_ref=template_ref)
    return len(candidates)


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def is_excluded(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDED_SCAFFOLD_PATTERNS)


def is_managed_update(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in MANAGED_UPDATE_PATTERNS)


def path_requested(rel: str, only_prefixes: list[str] | None) -> bool:
    if only_prefixes is None:
        return True
    return any(rel == prefix or rel.startswith(f"{prefix}/") for prefix in only_prefixes)


def parse_only(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    prefixes = [item.strip().strip("/").replace("\\", "/") for item in raw.split(",")]
    return [item for item in prefixes if item]


def same_file_content(left: Path, right: Path) -> bool:
    try:
        return left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def write_manifest(
    root: Path,
    *,
    template_ref: str = "",
    cli_install_spec: str | None = None,
) -> None:
    pops_dir = root / ".pops"
    pops_dir.mkdir(parents=True, exist_ok=True)
    manifest = pops_dir / "manifest.toml"
    existing = read_manifest(manifest)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    project = as_table(existing.get("project"))
    project["tool"] = "pops"
    project["updated_at"] = now

    scaffold = as_table(existing.get("scaffold"))
    scaffold["package"] = PACKAGE_NAME
    scaffold["version"] = package_version()
    scaffold["source"] = UPSTREAM_REPO
    if template_ref:
        scaffold["template_ref"] = template_ref

    merged = dict(existing)
    merged["project"] = project
    merged["scaffold"] = scaffold

    if cli_install_spec is not None:
        cli = as_table(existing.get("cli"))
        cli["package"] = PACKAGE_NAME
        cli["version"] = package_version()
        cli["install_spec"] = cli_install_spec
        cli["venv"] = ".venv"
        cli["updated_at"] = now
        merged["cli"] = cli

    manifest.write_text(dumps_manifest_toml(merged), encoding="utf-8")


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def as_table(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def dumps_manifest_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in ordered_manifest_sections(data):
        value = data[section]
        if isinstance(value, dict):
            append_toml_table(lines, section, value)
        else:
            lines.append(f"{toml_key(section)} = {toml_value(value)}")
    return "\n".join(lines).rstrip() + "\n"


def ordered_manifest_sections(data: dict[str, Any]) -> list[str]:
    preferred = ["project", "scaffold", "cli"]
    return [item for item in preferred if item in data] + [
        item for item in data if item not in preferred
    ]


def append_toml_table(lines: list[str], name: str, table: dict[str, Any]) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(f"[{toml_dotted_key(name)}]")
    nested: list[tuple[str, dict[str, Any]]] = []
    for key, value in table.items():
        if isinstance(value, dict):
            nested.append((key, value))
        else:
            lines.append(f"{toml_key(key)} = {toml_value(value)}")
    for key, value in nested:
        append_toml_table(lines, f"{name}.{key}", value)


def toml_dotted_key(name: str) -> str:
    return ".".join(toml_key(part) for part in name.split("."))


def toml_key(key: str) -> str:
    if key and all(char.isascii() and (char.isalnum() or char in "_-") for char in key):
        return key
    return f'"{escape_toml(key)}"'


def toml_value(value: object) -> str:
    if isinstance(value, str):
        return f'"{escape_toml(value)}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    return f'"{escape_toml(str(value))}"'


def escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


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


def bootstrap_project(
    root: Path,
    *,
    skip_venv: bool,
    skip_install: bool,
    install_spec: str,
) -> bool:
    venv_dir = root / ".venv"
    if venv_dir.exists():
        print(".venv already exists.")
    elif skip_venv:
        print("Skipped .venv creation.")
        if not skip_install:
            print("Skipped project-local pops install because .venv is missing.")
        return True
    else:
        created = run_make_venv(root)
        if not created:
            return False

    if skip_install:
        print("Skipped project-local pops install.")
        return True

    return install_project_cli(root, install_spec=install_spec or default_install_spec())


def run_make_venv(root: Path) -> bool:
    print("Creating .venv via make venv...")
    try:
        result = subprocess.run(["make", "venv"], cwd=root, check=False)
    except FileNotFoundError:
        print("make was not found; falling back to python -m venv .venv")
        result = run_python_venv(root)
    if result.returncode != 0:
        print("make venv failed; falling back to python -m venv .venv")
        result = run_python_venv(root)
    if result.returncode != 0:
        print("error: failed to create .venv", file=sys.stderr)
        return False
    return True


def run_python_venv(root: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=root, check=False)


def install_project_cli(root: Path, *, install_spec: str) -> bool:
    python = project_venv_python(root)
    if not python.exists():
        print(f"error: .venv Python was not found: {python}", file=sys.stderr)
        return False

    command, label = build_install_command(python, install_spec)
    print(f"Installing project-local pops via {label}: {install_spec}")
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        print(f"error: failed to install project-local pops: {exc}", file=sys.stderr)
        return False

    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        print(
            f"error: failed to install project-local pops: {message[:500]}",
            file=sys.stderr,
        )
        return False

    write_manifest(root, cli_install_spec=install_spec)
    print(f"Project-local pops is ready: {project_venv_pops(root)}")
    return True


def build_install_command(python: Path, install_spec: str) -> tuple[list[str], str]:
    uv = shutil.which("uv")
    if uv:
        return (
            [uv, "pip", "install", "--python", str(python), install_spec],
            "uv pip install",
        )
    return (
        [str(python), "-m", "pip", "install", install_spec],
        "python -m pip install",
    )


def default_install_spec() -> str:
    return f"{PACKAGE_NAME}=={package_version()}"


def project_venv_python(root: Path) -> Path:
    if sys.platform.startswith("win"):
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def project_venv_pops(root: Path) -> Path:
    if sys.platform.startswith("win"):
        return root / ".venv" / "Scripts" / "pops.exe"
    return root / ".venv" / "bin" / "pops"


def activate_command() -> str:
    if sys.platform.startswith("win"):
        return r".venv\Scripts\Activate.ps1"
    return "source .venv/bin/activate"


def print_next_steps(target: Path) -> None:
    print("Next steps:")
    print("  cd " + str(target))
    if not project_venv_pops(target).exists():
        print(f"  uvx --from {PACKAGE_NAME} pops setup")
    print("  " + activate_command())
    print("  pops doctor")


def check_project_local_cli(root: Path, warnings: list[str]) -> None:
    venv_dir = root / ".venv"
    if not venv_dir.exists():
        warnings.append(".venv is missing; run pops setup to create project-local pops.")
        return
    if not project_venv_python(root).exists():
        warnings.append(".venv exists but its Python executable was not found.")
    if not project_venv_pops(root).exists():
        warnings.append(
            "project-local pops was not found in .venv; run pops setup to install it."
        )


def print_manual_setup_hints(root: Path) -> None:
    if not (root / "refs" / "local" / "locations.toml").exists():
        print(
            "Manual: copy refs/local/locations.example.toml to "
            "refs/local/locations.toml when local paths are needed."
        )
    if not (root / "tex-env.toml").exists() and (root / "tex-env.example.toml").exists():
        print(
            "Optional: copy tex-env.example.toml to tex-env.toml when you need "
            "a custom TeX environment."
        )
    print("Run pops doctor after activating the project .venv.")


def check_path(root: Path, rel: str, errors: list[str]) -> None:
    if not (root / rel).exists():
        errors.append(f"missing {rel}")


def check_executable(name: str, warnings: list[str]) -> None:
    if shutil.which(name) is None:
        warnings.append(f"{name} is not on PATH")


def check_workflow_placeholders(root: Path, warnings: list[str]) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in sorted(workflows.glob("*.yml")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "YOUR_ORG/paperops" in text:
            warnings.append(f"workflow placeholder remains in {path.relative_to(root).as_posix()}")


def print_copy_summary(plan: CopyPlan) -> None:
    print(f"  copied: {len(plan.missing)}")
    print(f"  already present: {len(plan.unchanged)}")
    print(f"  different and left untouched: {len(plan.changed)}")
    print(f"  excluded: {len(plan.excluded)}")


def print_update_plan(plan: CopyPlan) -> None:
    print("Paperops update plan:")
    print(f"  missing managed files: {len(plan.missing)}")
    for rel in plan.missing[:20]:
        print(f"    + {rel}")
    if len(plan.missing) > 20:
        print(f"    ... {len(plan.missing) - 20} more")
    print(f"  changed managed files: {len(plan.changed)}")
    for rel in plan.changed[:20]:
        print(f"    ! {rel}")
    if len(plan.changed) > 20:
        print(f"    ... {len(plan.changed) - 20} more")
    print(f"  unchanged managed files: {len(plan.unchanged)}")


if __name__ == "__main__":
    raise SystemExit(main())
