"""Scratch rewrite archives for paper projects."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from paperops.cli.constants import EXCLUDED_SCAFFOLD_PATTERNS, SCAFFOLD_INCLUDE_EXCEPTIONS
from paperops.cli.manifest import dumps_manifest_toml, read_manifest
from paperops.cli.project import find_project_root
from paperops.cli.scaffold import scaffold_source


ARCHIVE_ROOT = "_archives"
DEFAULT_PART_SIZE_BYTES = 48 * 1024 * 1024
SCRATCH_ARCHIVE_PATHS = (
    "manuscript",
    "submission",
    "notes",
    "refs",
    "evidence",
    "claims",
    "review",
    "requests",
)
SCRATCH_RESET_PATHS = SCRATCH_ARCHIVE_PATHS + ("_handoff",)
ARCHIVE_EXCLUDED_PATTERNS = (
    "notes/session-context.generated.md",
    "manuscript/mirror/reports/latest.md",
    "manuscript/mirror/reports/smoke-check.md",
    "manuscript/shared/build/**",
    "submission/**/build/**",
    "submission/**/.tools/**",
    "refs/local/locations.toml",
    "refs/papers/**",
    "refs/research/**/results/**",
    "refs/research/**/report.generated.md",
    "refs/research/**/raw-findings.*",
    "refs/source-reach/**/raw/**",
    "refs/source-reach/**/doctor.generated.*",
    "refs/source-reach/**/capture.generated.*",
)


@dataclass(frozen=True)
class ScratchArchive:
    archive_id: str
    path: Path
    parts: list[str]
    sha256: str


def add_scratch_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    scratch_parser = subcommands.add_parser(
        "scratch",
        help="Archive, reset, and restore paper writing layers.",
    )
    scratch_subcommands = scratch_parser.add_subparsers(dest="scratch_action", required=True)

    archive_parser = scratch_subcommands.add_parser(
        "archive",
        help="Create a sealed split archive of manuscript layers.",
    )
    archive_parser.add_argument("path", nargs="?", type=Path, help="Project directory, defaults to cwd.")
    archive_parser.add_argument("--id", default="", help="Archive id, defaults to timestamp-label.")
    archive_parser.add_argument("--label", default="scratch archive", help="Human-readable archive label.")
    archive_parser.add_argument(
        "--include-handoff",
        action="store_true",
        help="Include _handoff payloads in the sealed archive.",
    )
    archive_parser.add_argument(
        "--part-size-mib",
        type=int,
        default=48,
        help="Maximum split bundle part size in MiB, defaults to 48.",
    )
    archive_parser.add_argument(
        "--part-size-bytes",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    archive_parser.set_defaults(func=cmd_scratch)

    restart_parser = scratch_subcommands.add_parser(
        "restart",
        help="Archive current writing layers, then reset them to the scaffold starter.",
    )
    restart_parser.add_argument("path", nargs="?", type=Path, help="Project directory, defaults to cwd.")
    restart_parser.add_argument("--id", default="", help="Archive id, defaults to timestamp-label.")
    restart_parser.add_argument("--label", default="scratch restart", help="Human-readable archive label.")
    restart_parser.add_argument(
        "--include-handoff",
        action="store_true",
        help="Include _handoff payloads in the sealed archive before reset.",
    )
    restart_parser.add_argument(
        "--part-size-mib",
        type=int,
        default=48,
        help="Maximum split bundle part size in MiB, defaults to 48.",
    )
    restart_parser.add_argument(
        "--part-size-bytes",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    restart_parser.add_argument("--yes", action="store_true", help="Confirm destructive reset after archive.")
    restart_parser.set_defaults(func=cmd_scratch)

    reset_parser = scratch_subcommands.add_parser(
        "reset",
        help="Reset manuscript layers to the bundled scaffold starter.",
    )
    reset_parser.add_argument("path", nargs="?", type=Path, help="Project directory, defaults to cwd.")
    reset_parser.add_argument("--yes", action="store_true", help="Confirm destructive reset.")
    reset_parser.add_argument(
        "--allow-without-archive",
        action="store_true",
        help="Allow reset even when no scratch archive exists.",
    )
    reset_parser.set_defaults(func=cmd_scratch)

    restore_parser = scratch_subcommands.add_parser(
        "restore",
        help="Restore manuscript layers from a sealed scratch archive.",
    )
    restore_parser.add_argument("first", help="Archive id, or project path when followed by archive id.")
    restore_parser.add_argument("second", nargs="?", help="Archive id when the first argument is a path.")
    restore_parser.add_argument("--yes", action="store_true", help="Confirm destructive restore.")
    restore_parser.set_defaults(func=cmd_scratch)

    list_parser = scratch_subcommands.add_parser("list", help="List scratch archives.")
    list_parser.add_argument("path", nargs="?", type=Path, help="Project directory, defaults to cwd.")
    list_parser.set_defaults(func=cmd_scratch)

    inspect_parser = scratch_subcommands.add_parser("inspect", help="Show scratch archive metadata.")
    inspect_parser.add_argument("first", help="Archive id, or project path when followed by archive id.")
    inspect_parser.add_argument("second", nargs="?", help="Archive id when the first argument is a path.")
    inspect_parser.set_defaults(func=cmd_scratch)
    return scratch_parser


def cmd_scratch(args: argparse.Namespace) -> int:
    path, archive_id = scratch_path_and_archive(args)
    root = find_project_root(path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2

    args.project_root = root
    try:
        if args.scratch_action == "archive":
            part_size = args.part_size_bytes or args.part_size_mib * 1024 * 1024
            archive = create_scratch_archive(
                root,
                archive_id=args.id,
                label=args.label,
                include_handoff=args.include_handoff,
                part_size_bytes=part_size,
            )
            print(f"Archived scratch state: {archive.archive_id}")
            print(f"Archive directory: {archive.path}")
            print(f"Bundle parts: {len(archive.parts)}")
            print("Note: sealed archives are not read during normal AI writing workflows.")
            return 0
        if args.scratch_action == "restart":
            if not args.yes:
                print("error: scratch restart resets writing layers after archiving; re-run with --yes.", file=sys.stderr)
                return 2
            part_size = args.part_size_bytes or args.part_size_mib * 1024 * 1024
            archive = create_scratch_archive(
                root,
                archive_id=args.id,
                label=args.label,
                include_handoff=args.include_handoff,
                part_size_bytes=part_size,
            )
            print(f"Archived scratch state: {archive.archive_id}")
            print(f"Archive directory: {archive.path}")
            print(f"Bundle parts: {len(archive.parts)}")
            copied = reset_scratch_layers(root, require_archive=False)
            print(f"Reset scratch writing layers from scaffold: {copied} files")
            print("Sealed archives remain under _archives/.")
            return 0
        if args.scratch_action == "reset":
            if not args.yes:
                print("error: scratch reset is destructive; re-run with --yes.", file=sys.stderr)
                return 2
            copied = reset_scratch_layers(root, require_archive=not args.allow_without_archive)
            print(f"Reset scratch writing layers from scaffold: {copied} files")
            print("Sealed archives remain under _archives/.")
            return 0
        if args.scratch_action == "restore":
            if not args.yes:
                print("error: scratch restore is destructive; re-run with --yes.", file=sys.stderr)
                return 2
            part_count = restore_scratch_archive(root, archive_id)
            print(f"Restored scratch archive: {archive_id}")
            print(f"Bundle parts read: {part_count}")
            return 0
        if args.scratch_action == "list":
            rows = list_scratch_archives(root)
            if not rows:
                print("No scratch archives found.")
                return 0
            for row in rows:
                print(f"{row['id']}\t{row['created_at']}\t{row['label']}")
            return 0
        if args.scratch_action == "inspect":
            info = inspect_scratch_archive(root, archive_id)
            parts = info.get("parts", [])
            paths = info.get("paths", [])
            print(f"id: {info.get('id', archive_id)}")
            print(f"label: {info.get('label', '')}")
            print(f"created_at: {info.get('created_at', '')}")
            print(f"format: {info.get('format', '')}")
            print(f"parts: {len(parts) if isinstance(parts, list) else 0}")
            print(f"part_size_bytes: {info.get('part_size_bytes', DEFAULT_PART_SIZE_BYTES)}")
            print(f"paths: {', '.join(str(item) for item in paths) if isinstance(paths, list) else ''}")
            return 0
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"error: unknown scratch action: {args.scratch_action}", file=sys.stderr)
    return 2


def scratch_path_and_archive(args: argparse.Namespace) -> tuple[Path | None, str]:
    if args.scratch_action not in {"restore", "inspect"}:
        return args.path, ""
    if args.second is None:
        return None, args.first
    first_path = Path(args.first)
    if first_path.exists() or any(sep in args.first for sep in ("/", "\\")):
        return first_path, args.second
    return Path(args.second), args.first


def create_scratch_archive(
    root: Path,
    *,
    archive_id: str,
    label: str,
    include_handoff: bool = False,
    part_size_bytes: int = DEFAULT_PART_SIZE_BYTES,
) -> ScratchArchive:
    if part_size_bytes <= 0:
        raise ValueError("part size must be positive")

    archive_id = archive_id or default_archive_id(label)
    if not is_safe_archive_id(archive_id):
        raise ValueError("archive id may contain only letters, numbers, dots, underscores, and hyphens")

    archive_root = ensure_archive_guidance(root)
    archive_dir = archive_root / archive_id
    if archive_dir.exists():
        raise FileExistsError(f"archive already exists: {archive_id}")
    archive_dir.mkdir(parents=True)

    paths = list(SCRATCH_ARCHIVE_PATHS)
    if include_handoff:
        paths.append("_handoff")

    with tempfile.TemporaryDirectory(prefix="paperops-scratch-") as tmp:
        bundle = Path(tmp) / "archive.zip"
        write_zip_bundle(root, bundle, paths)
        digest = file_sha256(bundle)
        parts = split_file(bundle, archive_dir, part_size_bytes=part_size_bytes)

    manifest = {
        "scratch_archive": {
            "id": archive_id,
            "label": label,
            "created_at": utc_now(),
            "format": "split-zip",
            "bundle_sha256": digest,
            "part_size_bytes": part_size_bytes,
            "include_handoff": include_handoff,
            "paths": paths,
            "parts": parts,
        }
    }
    (archive_dir / "manifest.toml").write_text(dumps_manifest_toml(manifest), encoding="utf-8")
    (archive_dir / "README.md").write_text(archive_readme(archive_id, label), encoding="utf-8")
    return ScratchArchive(archive_id=archive_id, path=archive_dir, parts=parts, sha256=digest)


def reset_scratch_layers(
    root: Path,
    *,
    require_archive: bool,
) -> int:
    if require_archive and not list_scratch_archives(root):
        raise FileNotFoundError("no scratch archive exists; run `pops scratch archive` first")
    clear_paths(root, SCRATCH_RESET_PATHS)
    copied = copy_scaffold_paths(root, SCRATCH_RESET_PATHS)
    ensure_archive_guidance(root)
    return copied


def restore_scratch_archive(root: Path, archive_id: str) -> int:
    archive_dir = archive_dir_for(root, archive_id)
    manifest = read_archive_manifest(archive_dir)
    scratch = manifest.get("scratch_archive")
    if not isinstance(scratch, dict):
        raise FileNotFoundError(f"scratch archive not found: {archive_id}")

    parts = [str(item) for item in scratch.get("parts", [])]
    if not parts:
        raise ValueError(f"scratch archive has no bundle parts: {archive_id}")
    expected_sha256 = str(scratch.get("bundle_sha256", ""))

    with tempfile.TemporaryDirectory(prefix="paperops-scratch-restore-") as tmp:
        bundle = Path(tmp) / "archive.zip"
        with bundle.open("wb") as out:
            for part in parts:
                part_path = archive_dir / part
                if not part_path.is_file():
                    raise FileNotFoundError(f"archive part is missing: {part_path}")
                out.write(part_path.read_bytes())
        actual_sha256 = file_sha256(bundle)
        if expected_sha256 and actual_sha256 != expected_sha256:
            raise ValueError("scratch archive checksum mismatch")

        validate_zip_members(bundle, root)
        clear_paths(root, SCRATCH_RESET_PATHS)
        extract_zip_safely(bundle, root)
    if not (root / "_handoff" / "README.md").exists():
        copy_scaffold_paths(root, ("_handoff",))
    ensure_archive_guidance(root)
    return len(parts)


def list_scratch_archives(root: Path) -> list[dict[str, str]]:
    archive_root = root / ARCHIVE_ROOT
    if not archive_root.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for manifest_path in sorted(archive_root.glob("*/manifest.toml")):
        data = read_archive_manifest(manifest_path.parent).get("scratch_archive")
        if not isinstance(data, dict):
            continue
        rows.append(
            {
                "id": str(data.get("id", manifest_path.parent.name)),
                "label": str(data.get("label", "")),
                "created_at": str(data.get("created_at", "")),
                "path": manifest_path.parent.as_posix(),
            }
        )
    return rows


def inspect_scratch_archive(root: Path, archive_id: str) -> dict[str, object]:
    archive_dir = archive_dir_for(root, archive_id)
    data = read_archive_manifest(archive_dir)
    scratch = data.get("scratch_archive")
    if not isinstance(scratch, dict):
        raise FileNotFoundError(f"scratch archive not found: {archive_id}")
    return scratch


def ensure_archive_guidance(root: Path) -> Path:
    archive_root = root / ARCHIVE_ROOT
    archive_root.mkdir(parents=True, exist_ok=True)
    agents = archive_root / "AGENTS.md"
    if not agents.exists():
        agents.write_text(archive_agents_text(), encoding="utf-8")
    readme = archive_root / "README.md"
    if not readme.exists():
        readme.write_text(archive_root_readme(), encoding="utf-8")
    return archive_root


def write_zip_bundle(root: Path, bundle: Path, paths: list[str]) -> None:
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel_root in paths:
            source = root / rel_root
            if not source.exists():
                continue
            for path in sorted(source.rglob("*")):
                if path.is_dir():
                    continue
                rel = path.relative_to(root).as_posix()
                if should_exclude_from_archive(rel):
                    continue
                archive.write(path, rel)


def split_file(bundle: Path, archive_dir: Path, *, part_size_bytes: int) -> list[str]:
    parts: list[str] = []
    index = 1
    with bundle.open("rb") as src:
        while True:
            chunk = src.read(part_size_bytes)
            if not chunk:
                break
            name = f"archive.zip.part{index:04d}"
            (archive_dir / name).write_bytes(chunk)
            parts.append(name)
            index += 1
    if not parts:
        name = "archive.zip.part0001"
        (archive_dir / name).write_bytes(b"")
        parts.append(name)
    return parts


def clear_paths(root: Path, paths: tuple[str, ...]) -> None:
    for rel in paths:
        path = root / rel
        if not path.exists():
            continue
        resolved = path.resolve()
        if not is_relative_to(resolved, root.resolve()):
            raise ValueError(f"refusing to remove outside project: {resolved}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def copy_scaffold_paths(root: Path, paths: tuple[str, ...]) -> int:
    copied = 0
    with scaffold_source() as source:
        for rel_root in paths:
            src_root = source / rel_root
            if not src_root.exists():
                continue
            for src in sorted(src_root.rglob("*")):
                rel = src.relative_to(source)
                if should_exclude_from_scaffold_reset(rel.as_posix()):
                    continue
                dst = root / rel
                if src.is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
    return copied


def extract_zip_safely(bundle: Path, root: Path) -> None:
    validate_zip_members(bundle, root)
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(root)


def validate_zip_members(bundle: Path, root: Path) -> None:
    resolved_root = root.resolve()
    with zipfile.ZipFile(bundle) as archive:
        for member in archive.infolist():
            parts = PurePosixPath(member.filename).parts
            if not parts or parts[0] not in SCRATCH_RESET_PATHS:
                raise ValueError(f"unsafe archive member: {member.filename}")
            target = (root / member.filename).resolve()
            if not is_relative_to(target, resolved_root):
                raise ValueError(f"unsafe archive member: {member.filename}")


def read_archive_manifest(archive_dir: Path) -> dict[str, object]:
    return read_manifest(archive_dir / "manifest.toml")


def archive_dir_for(root: Path, archive_id: str) -> Path:
    if not is_safe_archive_id(archive_id):
        raise ValueError(
            "archive id may contain only letters, numbers, dots, underscores, and hyphens"
        )
    return root / ARCHIVE_ROOT / archive_id


def should_exclude_from_archive(rel: str) -> bool:
    if rel.endswith(".pdf") and not rel.startswith("manuscript/shared/figures/"):
        return True
    return any(fnmatch(rel, pattern) for pattern in ARCHIVE_EXCLUDED_PATTERNS)


def should_exclude_from_scaffold_reset(rel: str) -> bool:
    if rel in SCAFFOLD_INCLUDE_EXCEPTIONS:
        return False
    return any(fnmatch(rel, pattern) for pattern in EXCLUDED_SCAFFOLD_PATTERNS)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_archive_id(label: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    slug = slugify(label) or "scratch"
    return f"{stamp}-{slug}"


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9._-]+", "-", lowered)
    return lowered.strip("-")[:48]


def is_safe_archive_id(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def archive_agents_text() -> str:
    return """# _archives/ AGENTS.md

このディレクトリは sealed scratch archive である。

- 通常の執筆、`/resume-session`、`/finish-manuscript`、査読、polish、関連研究では読まない。
- ユーザーが明示的に restore / inspect archive content / compare with archive を依頼した場合だけ扱う。
- 復元は `uvx --from paper-harness-cli pops scratch restore <id>` を使う。
- 展開済みの `manuscript/`、`notes/`、`refs/` などをここへ commit しない。
"""


def archive_root_readme() -> str:
    return """# _archives

過去の原稿状態を sealed bundle として保存する場所。

通常の AI 執筆では参照しない。復元や比較が必要な場合だけ `pops scratch` を使う。
"""


def archive_readme(archive_id: str, label: str) -> str:
    return f"""# {archive_id}

sealed scratch archive.

- label: {label}
- bundle: `archive.zip.partNNNN`
- restore: `uvx --from paper-harness-cli pops scratch restore {archive_id} --yes`

通常の執筆ではこの archive の内容を参照しない。
"""
