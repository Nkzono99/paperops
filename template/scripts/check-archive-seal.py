#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


MAX_ARCHIVE_PART_BYTES = 100 * 1024 * 1024
EXPANDED_LAYER_NAMES = {
    "manuscript",
    "submission",
    "notes",
    "refs",
    "evidence",
    "claims",
    "review",
    "requests",
    "_paperops",
    "_handoff",
}
TOP_LEVEL_ALLOWED_FILES = {"AGENTS.md", "README.md", ".gitkeep"}
ARCHIVE_ALLOWED_FILES = {"manifest.toml", "README.md"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that _archives contains sealed split bundles only."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check_archive_seal(root)

    print("# archive-seal-check")
    print("")
    if findings:
        print("## Errors")
        for finding in findings:
            print(f"- {finding}")
        print("")
        return 1
    print("_archives/ は sealed bundle だけを含んでいます。")
    return 0


def check_archive_seal(root: Path) -> list[str]:
    archive_root = root / "_archives"
    if not archive_root.exists():
        return []
    findings: list[str] = []
    for path in sorted(archive_root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path == archive_root:
            continue
        relative_to_archives = path.relative_to(archive_root)
        parts = relative_to_archives.parts
        if not parts:
            continue
        if len(parts) == 1:
            if path.is_file() and path.name not in TOP_LEVEL_ALLOWED_FILES:
                findings.append(f"`{rel}` は _archives/ 直下に置けないファイルです")
            continue

        if parts[1] in EXPANDED_LAYER_NAMES:
            findings.append(f"`{rel}` は expanded archive content です。sealed bundle にしてください")
            continue

        if path.is_dir():
            continue
        if path.name in ARCHIVE_ALLOWED_FILES or is_archive_part(path.name):
            if is_archive_part(path.name) and path.stat().st_size >= MAX_ARCHIVE_PART_BYTES:
                findings.append(f"`{rel}` が GitHub の単一ファイル制限 100MB 以上です")
            continue
        findings.append(f"`{rel}` は sealed archive で許可されていないファイルです")
    return findings


def is_archive_part(name: str) -> bool:
    if not name.startswith("archive.zip.part"):
        return False
    suffix = name.removeprefix("archive.zip.part")
    return len(suffix) == 4 and suffix.isdigit()


if __name__ == "__main__":
    raise SystemExit(main())
