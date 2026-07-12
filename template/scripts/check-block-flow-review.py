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
from paperops_typed_views import indexed_documents, workflow_projection


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
    return {key: value.upper() for key, value in workflow_projection(root)["sections"].items()}


def overall_state(root: Path) -> str:
    return str(workflow_projection(root)["stage"]).upper()


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
    sections = [item for item in indexed_documents(root, "manuscript", "section") if item.document.get("section_kind") == section]
    section_ids = {item.object_id for item in sections}
    return [item.path for item in indexed_documents(root, "manuscript", "block") if item.document.get("section_id") in section_ids]


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
    sections = {str(item.document.get("section_kind")): item for item in indexed_documents(root, "manuscript", "section")}
    blocks = {item.object_id: item for item in indexed_documents(root, "manuscript", "block")}
    for section in ["results", "discussion"]:
        record = sections.get(section)
        if record is None:
            continue
        section_state = str(record.document.get("status", ""))
        if section_state not in {"verified", "stale"}:
            continue
        ordered = set(record.document.get("ordered_block_ids", []))
        if not ordered:
            findings.append(
                Finding(
                    severity,
                    f"typed Manuscript section `{record.object_id}` は {section_state} ですが ordered block がありません。",
                )
            )
            continue
        missing = ordered - set(blocks)
        if missing:
            findings.append(
                Finding(
                    severity,
                    f"typed Manuscript section `{record.object_id}` が未登録 block を参照しています: " + ", ".join(sorted(missing)),
                )
            )
        for block_id in sorted(ordered & set(blocks)):
            document = blocks[block_id].document
            if not meaningful(str(document.get("reader_task", ""))) or document.get("operation") not in {"keep", "compress", "move", "merge", "split", "cut", "rewrite", "add"}:
                findings.append(
                    Finding(
                        severity,
                        f"typed Manuscript block `{block_id}` の reader task / operation が未完了です。",
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
