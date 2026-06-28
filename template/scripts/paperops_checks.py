"""Shared helpers for template checker scripts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


@dataclass(frozen=True)
class MarkdownTable:
    headers: list[str]
    rows: list[dict[str, str]]
    source: Path | None = None


PLACEHOLDER_VALUES = {
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
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_mapping(path: Path) -> dict[str, Any]:
    try:
        text = read_text(path)
    except OSError:
        return {}
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    collected: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(collected)
        collected.append(line)
    return ""


def clean_value(value: str, *, strip_code: bool = False) -> str:
    cleaned = value.strip()
    if strip_code:
        cleaned = cleaned.strip("`").strip()
    return cleaned.strip('"').strip("'")


def meaningful_value(value: str, *, placeholders: set[str] | None = None, strip_code: bool = False) -> bool:
    all_placeholders = PLACEHOLDER_VALUES | (placeholders or set())
    return clean_value(value, strip_code=strip_code).lower() not in all_placeholders


def field_block(front: str, key: str) -> str:
    lines = front.splitlines()
    collected: list[str] = []
    in_block = False
    for line in lines:
        if re.match(rf"^{re.escape(key)}:\s*", line):
            in_block = True
            collected.append(line)
            continue
        if in_block:
            if line and not line.startswith((" ", "\t", "-")):
                break
            collected.append(line)
    return "\n".join(collected)


def scalar_value(front: str, key: str, *, strip_code: bool = False) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(front)
    if not match:
        return ""
    return clean_value(match.group(1), strip_code=strip_code)


def nested_scalar(front: str, parent: str, key: str, *, strip_code: bool = False) -> str:
    block = field_block(front, parent)
    pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return ""
    return clean_value(match.group(1), strip_code=strip_code)


def field_values(
    front: str,
    key: str,
    *,
    placeholders: set[str] | None = None,
    strip_code: bool = False,
) -> list[str]:
    block = field_block(front, key)
    if not block:
        return []
    first = block.splitlines()[0]
    inline = clean_value(first.split(":", 1)[1], strip_code=strip_code)
    if inline.startswith("[") and inline.endswith("]"):
        return [
            clean_value(item, strip_code=strip_code)
            for item in inline[1:-1].split(",")
            if meaningful_value(item, placeholders=placeholders, strip_code=strip_code)
        ]
    if meaningful_value(inline, placeholders=placeholders, strip_code=strip_code):
        return [inline]
    values: list[str] = []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        item = clean_value(stripped[1:], strip_code=strip_code)
        if meaningful_value(item, placeholders=placeholders, strip_code=strip_code):
            values.append(item)
    return values


def parse_markdown_tables(
    text: str,
    *,
    required_header: str | None = None,
    source: Path | None = None,
    strip_code: bool = True,
) -> list[MarkdownTable]:
    lines = text.splitlines()
    tables: list[MarkdownTable] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("|") or (required_header and required_header not in line):
            index += 1
            continue
        headers = [clean_value(cell, strip_code=strip_code) for cell in line.strip("|").split("|")]
        if required_header and required_header not in headers:
            index += 1
            continue
        index += 1
        if index < len(lines):
            separator = lines[index].strip().replace("|", "").replace(" ", "")
            if separator and set(separator) <= {"-", ":"}:
                index += 1
        rows: list[dict[str, str]] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            cells = [
                clean_value(cell, strip_code=strip_code)
                for cell in lines[index].strip().strip("|").split("|")
            ]
            if len(cells) < len(headers):
                cells.extend([""] * (len(headers) - len(cells)))
            rows.append(dict(zip(headers, cells)))
            index += 1
        tables.append(MarkdownTable(headers=headers, rows=rows, source=source))
    return tables


def warning_severity(strict: bool) -> str:
    return "error" if strict else "warning"


def partition_findings(findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return errors, warnings


def emit_findings(
    title: str,
    findings: list[Finding],
    *,
    success_message: str,
    fail_on_warnings: bool = False,
) -> int:
    errors, warnings = partition_findings(findings)

    print(f"# {title}")
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
        print(success_message)

    return 1 if errors or (fail_on_warnings and warnings) else 0
