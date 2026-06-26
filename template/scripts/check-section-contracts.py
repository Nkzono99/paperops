#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import display_path, internal_path


PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|置き換えてください)")

REQUIRED_RESULTS_FIELDS = [
    ("reader_question", "`reader question`"),
    ("one_sentence_answer", "`one-sentence answer`"),
    ("quantitative_evidence_and_unit_of_analysis", "`quantitative evidence and unit of analysis`"),
    ("figure_table_role", "`figure / table role`"),
    ("baseline_comparator_rationale", "`baseline / comparator rationale`"),
    ("consequence", "`consequence`"),
]

REQUIRED_DISCUSSION_FIELDS = [
    "principal_finding",
    "mechanism_warrant",
    "prior_work_delta",
    "alternative_or_boundary",
    "implication",
    "decisive_next_test",
]

REQUIRED_METHOD_REGISTRY_ROWS = [
    "estimand_and_unit_of_analysis",
    "comparison_or_baseline",
    "decision_criteria",
    "verification_or_convergence",
]


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


def severity(strict: bool) -> str:
    return "error" if strict else "warning"


def normalize_key(value: str) -> str:
    cleaned = value.strip().lower().replace("`", "")
    cleaned = re.sub(r"\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    aliases = {
        "reader_question": "reader_question",
        "one_sentence_answer": "one_sentence_answer",
        "quantitative_evidence_and_unit_of_analysis": "quantitative_evidence_and_unit_of_analysis",
        "quantitative_evidence_unit_of_analysis": "quantitative_evidence_and_unit_of_analysis",
        "figure_table_role": "figure_table_role",
        "figure_table_role": "figure_table_role",
        "baseline_comparator_rationale": "baseline_comparator_rationale",
        "baseline_or_comparator_rationale": "baseline_comparator_rationale",
        "comparison_baseline_rationale": "baseline_comparator_rationale",
    }
    return aliases.get(cleaned, cleaned)


def resolve_storyline_path(root: Path) -> tuple[str, Path] | None:
    for rel_path in ["notes/views/storyline.md", "notes/storyline.md"]:
        path = internal_path(root, rel_path)
        if path.exists():
            return display_path(root, path), path
    return None


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def extract_bullet_map(body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    pattern = re.compile(r"^[ \t]*-[ \t]*([^:]+):[ \t]*(.*)$", re.MULTILINE)
    for match in pattern.finditer(body):
        values[normalize_key(match.group(1))] = match.group(2).strip()
    return values


def normalize_header(value: str) -> str:
    return normalize_key(value)


def extract_table_rows(body: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in cells):
            continue
        normalized = [normalize_header(cell) for cell in cells]
        if "item" in normalized and "definition_location" in normalized:
            headers = normalized
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def check_results_hierarchy(rel_path: str, body: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    if not body.strip():
        return [
            Finding(
                severity(strict),
                f"`{rel_path}` に Results hierarchy がありません",
            )
        ]
    values = extract_bullet_map(body)
    for key, label in REQUIRED_RESULTS_FIELDS:
        if is_blank(values.get(key)):
            findings.append(
                Finding(
                    severity(strict),
                    f"`{rel_path}` の Results hierarchy で {label} が未記入です",
                )
            )
    return findings


def check_discussion_functions(rel_path: str, body: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    if not body.strip():
        return [
            Finding(
                severity(strict),
                f"`{rel_path}` に Discussion functions がありません",
            )
        ]
    values = extract_bullet_map(body)
    for key in REQUIRED_DISCUSSION_FIELDS:
        if is_blank(values.get(key)):
            findings.append(
                Finding(
                    severity(strict),
                    f"`{rel_path}` の discussion functions で `{key}` が未記入です",
                )
            )
    return findings


def check_methods_registry(rel_path: str, body: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    rows = extract_table_rows(body)
    if not rows:
        return [
            Finding(
                severity(strict),
                f"`{rel_path}` に Methods definition registry がありません",
            )
        ]
    by_item = {normalize_key(row.get("item", "")): row for row in rows}
    for item in REQUIRED_METHOD_REGISTRY_ROWS:
        row = by_item.get(item)
        if row is None:
            findings.append(
                Finding(
                    severity(strict),
                    f"`{rel_path}` の Methods definition registry に `{item}` がありません",
                )
            )
            continue
        if is_blank(row.get("definition_location")):
            findings.append(
                Finding(
                    severity(strict),
                    f"`{rel_path}` の Methods definition registry `{item}` の definition location が未記入です",
                )
            )
        if is_blank(row.get("manuscript_block")):
            findings.append(
                Finding(
                    severity(strict),
                    f"`{rel_path}` の Methods definition registry `{item}` の manuscript block が未記入です",
                )
            )
    return findings


def check(root: Path, text: str, rel_path: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_results_hierarchy(rel_path, section_body(text, "Results hierarchy"), strict))
    findings.extend(check_discussion_functions(rel_path, section_body(text, "Discussion functions"), strict))
    findings.extend(check_methods_registry(rel_path, section_body(text, "Methods definition registry"), strict))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="storyline controlled view の Results / Discussion / Methods contract coverage を確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    resolved = resolve_storyline_path(root)
    if resolved is None:
        print("# section-contract-check")
        print("")
        print("## Errors")
        print("- `_paperops/notes/views/storyline.md` が見つかりません（旧互換: `notes/views/storyline.md`, `notes/storyline.md`）")
        return 1

    rel_path, path = resolved
    findings = check(root, read_text(path), rel_path, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# section-contract-check")
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
        print("section contracts は Results hierarchy / Discussion functions / Methods registry を満たしています。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
