#!/usr/bin/env python3
"""Detect authoring notes that leaked into reader-facing manuscript prose."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


MANUSCRIPT_DIRS = ("manuscript/ja/sections", "manuscript/en/sections")
SUPPRESSION_RE = re.compile(r"paperops:\s*allow-authoring-intent", re.IGNORECASE)
AUTHORING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "claim strengthening work plan",
        re.compile(r"claim\s*を\s*強め|claim\s*を\s*補強|主張\s*を\s*強め|主張\s*を\s*補強", re.IGNORECASE),
    ),
    (
        "additional work needed for claim",
        re.compile(r"必要な追加作業|追加作業.{0,30}(claim|主張)|(claim|主張).{0,30}追加作業", re.IGNORECASE),
    ),
    (
        "drafting meta note",
        re.compile(r"執筆上|執筆意図|執筆メモ|著者メモ|作業メモ|原稿メモ"),
    ),
    (
        "unresolved draft placeholder",
        re.compile(r"\b(?:TODO|TBD)\b|後で(?:埋める|書く|追記|整理)|後ほど(?:埋める|書く|追記|整理)", re.IGNORECASE),
    ),
    (
        "planned later fill",
        re.compile(r"(ここ|本節|この段落).{0,24}(?:予定|後で|後ほど).{0,24}(?:示す|説明|追記|整理|埋める)"),
    ),
    (
        "english authoring note",
        re.compile(r"\b(?:authoring|drafting|writing)\s+note\b", re.IGNORECASE),
    ),
    (
        "english claim strengthening plan",
        re.compile(r"\b(?:strengthen(?:ing)?\s+the\s+claim|claim.{0,40}strengthen|additional\s+work\s+(?:needed\s+to\s+)?strengthen)\b", re.IGNORECASE),
    ),
    (
        "english unresolved placeholder",
        re.compile(r"\b(?:TODO|TBD|placeholder|fill\s+in\s+later|add\s+later|to\s+be\s+added)\b", re.IGNORECASE),
    ),
)


@dataclass
class Finding:
    severity: str
    rel_path: str
    line_number: int
    pattern_name: str
    excerpt: str

    @property
    def message(self) -> str:
        return (
            f"`{self.rel_path}:{self.line_number}` に reader-facing ではない authoring intent "
            f"({self.pattern_name}) らしい表現があります: {self.excerpt}"
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def manuscript_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel_dir in MANUSCRIPT_DIRS:
        base = root / rel_dir
        if base.exists():
            files.extend(sorted(base.glob("*.tex")))
    return files


def split_tex_comment(line: str) -> tuple[str, str]:
    chars: list[str] = []
    escaped = False
    for index, char in enumerate(line):
        if char == "%" and not escaped:
            return "".join(chars), line[index + 1 :]
        chars.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return "".join(chars), ""


def clean_excerpt(text: str, limit: int = 120) -> str:
    excerpt = re.sub(r"\s+", " ", text).strip()
    if len(excerpt) > limit:
        excerpt = excerpt[: limit - 3].rstrip() + "..."
    return f"`{excerpt}`"


def check_file(root: Path, path: Path, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    rel_path = path.relative_to(root).as_posix()
    allow_next_content_line = False
    severity = "error" if strict else "warning"

    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        prose, comment = split_tex_comment(line)
        if SUPPRESSION_RE.search(comment):
            if prose.strip():
                continue
            allow_next_content_line = True
            continue
        stripped = prose.strip()
        if not stripped:
            continue
        if allow_next_content_line:
            allow_next_content_line = False
            continue
        for pattern_name, pattern in AUTHORING_PATTERNS:
            if pattern.search(stripped):
                findings.append(
                    Finding(
                        severity=severity,
                        rel_path=rel_path,
                        line_number=line_number,
                        pattern_name=pattern_name,
                        excerpt=clean_excerpt(stripped),
                    )
                )
                break
    return findings


def check(root: Path, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    for path in manuscript_files(root):
        findings.extend(check_file(root, path, strict=strict))
    return findings


def render(findings: list[Finding]) -> None:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# authoring-intent-check")
    print("")
    if errors:
        print("## Errors")
        for finding in errors:
            print(f"- {finding.message}")
        print("")
    if warnings:
        print("## Warnings")
        for finding in warnings:
            print(f"- {finding.message}")
        print("")
    if findings:
        print(
            "執筆上の意図、後で埋める内容、作業計画は本文 prose に置かず、"
            "`% INTENT:` または `% TODO-PAPER:` の TeX comment にするか、"
            "`_paperops/notes/` または typed Issue Model へ移してください。"
        )
        print("意図的に公開本文として扱う場合は直前行に `% paperops: allow-authoring-intent -- reason` を置いてください。")
    else:
        print("authoring intent leak は見つかりませんでした。")


def main() -> int:
    parser = argparse.ArgumentParser(description="公開原稿本文へ漏れた執筆メモ・作業計画を検出する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="検出した authoring intent leak を error にする。")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(root, strict=args.strict)
    render(findings)
    return 1 if any(finding.severity == "error" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
