#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|置き換えてください)")
BLOCK_RE = re.compile(r"%\s*block:\s*([A-Za-z0-9_.:-]+)")
REQUIRED_SPINE = ["reader_promise", "central_claim", "evidence_ladder", "scope_boundary"]
REQUIRED_FUNCTIONS = [
    "results_hierarchy",
    "mechanism_warrant",
    "prior_work_delta",
    "decisive_next_test",
]


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


def resolve_storyline_path(root: Path) -> tuple[str, Path] | None:
    candidates = [
        "notes/views/storyline.md",
        "notes/storyline.md",
    ]
    for rel_path in candidates:
        path = root / rel_path
        if path.exists():
            return rel_path, path
    return None


def extract_spine_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    pattern = re.compile(r"^\s*-\s*([A-Za-z0-9_/-]+):\s*(.*)$", re.MULTILINE)
    for match in pattern.finditer(text):
        values[match.group(1).strip()] = match.group(2).strip()
    return values


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def extract_section_depth_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in cells):
            continue
        lowered = [normalize_header(cell) for cell in cells]
        if "function" in lowered and "manuscript_block" in lowered:
            headers = lowered
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def manuscript_blocks(root: Path) -> set[str]:
    blocks: set[str] = set()
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return blocks
    for path in manuscript.rglob("*.tex"):
        blocks.update(BLOCK_RE.findall(read_text(path)))
    return blocks


def block_tokens(value: str) -> list[str]:
    if is_blank(value):
        return []
    cleaned = value.replace("`", "")
    return [
        token.strip()
        for token in re.split(r"[,;、\s]+", cleaned)
        if token.strip() and token.strip() not in {"-", "n/a", "none"}
    ]


def check(root: Path, text: str, rel_path: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    spine = extract_spine_values(text)
    for key in REQUIRED_SPINE:
        if is_blank(spine.get(key)):
            findings.append(Finding("error" if strict else "warning", f"`{rel_path}` の `{key}` が未記入です"))

    rows = extract_section_depth_rows(text)
    if not rows:
        findings.append(
            Finding("error" if strict else "warning", f"`{rel_path}` に Section depth map がありません")
        )
        return findings

    by_function = {row.get("function", "").strip(): row for row in rows}
    for function in REQUIRED_FUNCTIONS:
        row = by_function.get(function)
        if row is None:
            findings.append(
                Finding("error" if strict else "warning", f"`{rel_path}` の Section depth map に `{function}` がありません")
            )
            continue
        if is_blank(row.get("manuscript_block")):
            findings.append(
                Finding("error" if strict else "warning", f"`{function}` の manuscript block が未記入です")
            )

    for row in rows:
        function = row.get("function", "").strip()
        block_value = row.get("manuscript_block", "")
        if is_blank(function):
            findings.append(Finding("error" if strict else "warning", "Section depth map に function 未記入の行があります"))
        if is_blank(block_value):
            continue
        known_blocks = manuscript_blocks(root)
        for token in block_tokens(block_value):
            if known_blocks and token not in known_blocks:
                findings.append(
                    Finding(
                        "error" if strict else "warning",
                        f"`{function}` の manuscript block `{token}` が manuscript/*.tex に見つかりません",
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="storyline view と manuscript block の対応を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    resolved = resolve_storyline_path(root)
    if resolved is None:
        print("# storyline-check")
        print("")
        print("## Errors")
        print("- `notes/views/storyline.md` が見つかりません（旧互換: `notes/storyline.md`）")
        return 1
    rel_path, path = resolved
    findings = check(root, read_text(path), rel_path, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# storyline-check")
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
    if not findings:
        print("storyline view は required function と manuscript block に対応しています。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
