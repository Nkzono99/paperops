#!/usr/bin/env python3
"""Check block-flow review artifacts for audited Results / Discussion sections."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_checks import Finding, emit_findings, frontmatter, read_text, warning_severity
from paperops_paths import display_path, internal_path


TARGET_SECTIONS = {
    "results": ("30_results.tex",),
    "discussion": ("40_discussion.tex",),
}
REVIEWED_SECTION_STATES = {"AUDITED", "ACCEPTED"}
REQUIRED_COLUMNS = {
    "block_id",
    "reader_question",
    "author_move",
    "why_here",
    "next_block_expectation",
    "operation",
}
REQUIRED_NON_PLACEHOLDER = {
    "reader_question",
    "author_move",
    "why_here",
    "next_block_expectation",
    "operation",
}
ALLOWED_OPERATIONS = {"keep", "move", "split", "merge", "delete", "add"}
PLACEHOLDERS = {
    "",
    "[]",
    "{}",
    '""',
    "''",
    "unchecked",
    "未記入",
    "todo",
    "tbd",
    "none",
    "null",
    "n/a",
    "keep / move / split / merge / delete / add",
}
BLOCK_RE = re.compile(r"%\s*block:\s*([A-Za-z0-9_.:-]+)")


@dataclass(frozen=True)
class ReviewTable:
    path: Path
    headers: list[str]
    rows: list[dict[str, str]]


def load_mapping(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    return data if isinstance(data, dict) else {}


def section_states(root: Path) -> dict[str, str]:
    path = internal_path(root, "workflow", "current-state.yml")
    if not path.exists():
        return {}
    current = load_mapping(path)
    sections = current.get("sections", {})
    if not isinstance(sections, dict):
        return {}
    states: dict[str, str] = {}
    for name, section in sections.items():
        if isinstance(section, dict):
            states[str(name)] = str(section.get("state", "")).strip()
    return states


def manuscript_blocks(root: Path, section: str) -> set[str]:
    filenames = TARGET_SECTIONS.get(section, ())
    blocks: set[str] = set()
    manuscript = root / "manuscript"
    for language in ["ja", "en"]:
        section_dir = manuscript / language / "sections"
        for filename in filenames:
            path = section_dir / filename
            if path.exists():
                blocks.update(BLOCK_RE.findall(read_text(path)))
    return blocks


def clean(value: str) -> str:
    return value.strip().strip("`").strip().strip('"').strip("'")


def meaningful(value: str) -> bool:
    return clean(value).lower() not in PLACEHOLDERS


def scalar_value(front: str, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(front)
    if not match:
        return ""
    return clean(match.group(1))


def review_files(root: Path, section: str) -> list[Path]:
    base = internal_path(root, "review", "block-flow")
    if not base.exists():
        return []
    files: list[Path] = []
    for path in sorted(base.glob("*.md")):
        if path.name == "README.md" or path.name.endswith("-template.md"):
            continue
        front = frontmatter(read_text(path))
        if scalar_value(front, "section") == section:
            files.append(path)
    return files


def parse_tables(path: Path) -> list[ReviewTable]:
    lines = read_text(path).splitlines()
    tables: list[ReviewTable] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("|") or "block_id" not in line:
            index += 1
            continue
        headers = [clean(cell) for cell in line.strip("|").split("|")]
        if "block_id" not in headers:
            index += 1
            continue
        index += 1
        if index < len(lines) and set(lines[index].strip().replace("|", "").replace(" ", "")) <= {"-", ":"}:
            index += 1
        rows: list[dict[str, str]] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            cells = [clean(cell) for cell in lines[index].strip().strip("|").split("|")]
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            rows.append(dict(zip(headers, cells)))
            index += 1
        tables.append(ReviewTable(path=path, headers=headers, rows=rows))
    return tables


def review_rows(root: Path, section: str, findings: list[Finding], severity: str) -> dict[str, dict[str, str]]:
    rows_by_block: dict[str, dict[str, str]] = {}
    for path in review_files(root, section):
        tables = parse_tables(path)
        if not tables:
            findings.append(
                Finding(
                    severity,
                    f"`{display_path(root, path)}` に block operation table がありません。",
                )
            )
            continue
        for table in tables:
            missing_columns = REQUIRED_COLUMNS - set(table.headers)
            if missing_columns:
                findings.append(
                    Finding(
                        severity,
                        f"`{display_path(root, table.path)}` の block operation table に列がありません: "
                        + ", ".join(sorted(missing_columns)),
                    )
                )
                continue
            for row in table.rows:
                block_id = row.get("block_id", "")
                if not meaningful(block_id):
                    continue
                rows_by_block[block_id] = row
                operation = clean(row.get("operation", "")).lower()
                if operation and operation not in ALLOWED_OPERATIONS:
                    findings.append(
                        Finding(
                            severity,
                            f"`{display_path(root, table.path)}` の `{block_id}` operation `{operation}` は未知です。",
                        )
                    )
    return rows_by_block


def check(root: Path, strict: bool) -> list[Finding]:
    severity = warning_severity(strict)
    findings: list[Finding] = []
    states = section_states(root)
    for section in ["results", "discussion"]:
        if states.get(section) not in REVIEWED_SECTION_STATES:
            continue
        blocks = manuscript_blocks(root, section)
        if not blocks:
            findings.append(
                Finding(
                    severity,
                    f"`{section}` は {states.get(section)} ですが、manuscript section に `% block:` がありません。",
                )
            )
            continue
        files = review_files(root, section)
        if not files:
            findings.append(
                Finding(
                    severity,
                    f"`{section}` は {states.get(section)} ですが、"
                    "`_paperops/review/block-flow/` に block-flow review artifact がありません。",
                )
            )
            continue
        rows = review_rows(root, section, findings, severity)
        missing_blocks = blocks - set(rows)
        if missing_blocks:
            findings.append(
                Finding(
                    severity,
                    f"`{section}` の block-flow review に manuscript block がありません: "
                    + ", ".join(sorted(missing_blocks)),
                )
            )
        for block_id in sorted(blocks & set(rows)):
            row = rows[block_id]
            missing_fields = [
                field
                for field in sorted(REQUIRED_NON_PLACEHOLDER)
                if not meaningful(row.get(field, ""))
            ]
            if missing_fields:
                findings.append(
                    Finding(
                        severity,
                        f"`{section}` block `{block_id}` の block-flow review が未完了です: "
                        + ", ".join(missing_fields),
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AUDITED / ACCEPTED Results・Discussion の block-flow review artifact を確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    return emit_findings(
        "block-flow-review-check",
        check(root, strict=args.strict),
        success_message="block-flow review に問題は見つかりませんでした。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
