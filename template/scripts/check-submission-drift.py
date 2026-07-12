#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(?P<block_id>[A-Za-z0-9:._-]+)\s*$", re.MULTILINE)


def extract_blocks(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {match.group("block_id") for match in BLOCK_RE.finditer(path.read_text(encoding="utf-8", errors="replace"))}


def find_submission_mains(root: Path) -> list[Path]:
    submission = root / "submission"
    if not submission.exists():
        return []
    return sorted(path for path in submission.glob("*/main.tex") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="submission/<venue>/main.tex と manuscript/en の同期注意点を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="投稿前 gate として submission drift を error にする。")
    args = parser.parse_args()

    root = args.root.resolve()
    en_blocks: set[str] = set()
    for path in sorted((root / "manuscript/en").glob("**/*.tex")):
        en_blocks |= extract_blocks(path)

    print("# submission-drift-check")
    print("")
    mains = find_submission_mains(root)
    if not mains:
        print("submission/<venue>/main.tex はまだありません。投稿版 drift check をスキップします。")
        return 0

    warnings: list[str] = []
    for main_tex in mains:
        rel_path = main_tex.relative_to(root).as_posix()
        submission_blocks = extract_blocks(main_tex)
        if not submission_blocks:
            warnings.append(f"`{rel_path}` に `% block:` ID がありません。科学的変更は `manuscript/en` 側へ戻したか手動確認してください。")
            continue
        missing = sorted(en_blocks - submission_blocks)
        extra = sorted(submission_blocks - en_blocks)
        if missing:
            warnings.append(f"`{rel_path}` は manuscript/en の block を含んでいません: {', '.join(missing)}")
        if extra:
            warnings.append(f"`{rel_path}` には manuscript/en にない block があります: {', '.join(extra)}")

    if warnings:
        print("## Errors" if args.strict else "## Warnings")
        for warning in warnings:
            print(f"- {warning}")
        print("")
    else:
        print("submission と manuscript/en の block ID は対応しています。")
    return 1 if warnings and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
