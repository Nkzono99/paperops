#!/usr/bin/env python3
"""Check block-flow review artifacts for audited Results / Discussion sections."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from paperops_checks import (
    Finding,
    clean_value,
    emit_findings,
    frontmatter,
    load_mapping,
    meaningful_value,
    parse_markdown_tables,
    read_text,
    scalar_value,
    warning_severity,
)
from paperops_paths import display_path, internal_path


TARGET_SECTIONS = {
    "results": ("30_results.tex",),
    "discussion": ("40_discussion.tex",),
}
REVIEWED_SECTION_STATES = {"AUDITED", "ACCEPTED"}
STRUCTURE_ACCEPTED_OR_LATER = {"STRUCTURE_ACCEPTED", "POLISHED", "SUBMISSION_READY"}
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
EXTRA_PLACEHOLDERS = {
    "keep / move / split / merge / delete / add",
}
BLOCK_RE = re.compile(r"%\s*block:\s*([A-Za-z0-9_.:-]+)")


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


def overall_state(root: Path) -> str:
    path = internal_path(root, "workflow", "current-state.yml")
    if not path.exists():
        return ""
    current = load_mapping(path)
    overall = current.get("overall", {})
    if not isinstance(overall, dict):
        return ""
    return str(overall.get("state", "")).strip()


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


def meaningful(value: str) -> bool:
    return meaningful_value(value, placeholders=EXTRA_PLACEHOLDERS, strip_code=True)


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


def review_rows(root: Path, section: str, findings: list[Finding], severity: str) -> dict[str, dict[str, str]]:
    rows_by_block: dict[str, dict[str, str]] = {}
    for path in review_files(root, section):
        tables = parse_markdown_tables(read_text(path), required_header="block_id", source=path)
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
                        f"`{display_path(root, table.source or path)}` の block operation table に列がありません: "
                        + ", ".join(sorted(missing_columns)),
                    )
                )
                continue
            for row in table.rows:
                block_id = row.get("block_id", "")
                if not meaningful(block_id):
                    continue
                rows_by_block[block_id] = row
                operation = clean_value(row.get("operation", ""), strip_code=True).lower()
                if operation and operation not in ALLOWED_OPERATIONS:
                    findings.append(
                        Finding(
                            severity,
                            f"`{display_path(root, table.source or path)}` の `{block_id}` operation `{operation}` は未知です。",
                        )
                    )
    return rows_by_block


def check(root: Path, strict: bool) -> list[Finding]:
    severity = warning_severity(strict)
    findings: list[Finding] = []
    states = section_states(root)
    overall = overall_state(root)
    for section in ["results", "discussion"]:
        section_state = states.get(section)
        if overall in STRUCTURE_ACCEPTED_OR_LATER and section_state not in REVIEWED_SECTION_STATES:
            findings.append(
                Finding(
                    severity,
                    f"`{overall}` requires `{section}` to be AUDITED / ACCEPTED before structure acceptance, "
                    f"but current section state is `{section_state}`.",
                )
            )
            continue
        if section_state not in REVIEWED_SECTION_STATES:
            continue
        blocks = manuscript_blocks(root, section)
        if not blocks:
            findings.append(
                Finding(
                    severity,
                    f"`{section}` は {section_state} ですが、manuscript section に `% block:` がありません。",
                )
            )
            continue
        files = review_files(root, section)
        if not files:
            findings.append(
                Finding(
                    severity,
                    f"`{section}` は {section_state} ですが、"
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
