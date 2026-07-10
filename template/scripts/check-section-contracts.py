#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from paperops_checks import Finding, emit_findings, load_mapping, read_text, warning_severity
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

REQUIRED_TYPED_RESULTS_FIELDS = [
    "reader_question",
    "answer",
    "quantitative_evidence_and_unit_of_analysis",
    "figure_table_role",
    "baseline_comparator_rationale",
    "consequence",
]

TYPED_RESULTS_ID_RE = re.compile(r"^RHI-[A-Za-z0-9][A-Za-z0-9._-]*$")

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


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


def severity(strict: bool) -> str:
    return warning_severity(strict)


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


def resolve_results_hierarchy_path(root: Path) -> Path:
    return root / "_paperops" / "model" / "editorial" / "results-hierarchy.yml"


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


def extract_legacy_results_items(body: str) -> list[tuple[str, dict[str, str]]]:
    items: list[tuple[str, dict[str, str]]] = []
    current_label = "1"
    current_values: dict[str, str] | None = None
    pattern = re.compile(r"^[ \t]*-[ \t]*([^:]+):[ \t]*(.*)$", re.MULTILINE)
    for match in pattern.finditer(body):
        raw_key = match.group(1).strip()
        key = normalize_key(raw_key)
        if key == "reader_question":
            if current_values is not None:
                items.append((current_label, current_values))
            suffix = re.search(r"(\d+)\s*$", raw_key)
            current_label = suffix.group(1) if suffix else str(len(items) + 1)
            current_values = {}
        elif current_values is None:
            current_values = {}
        current_values[key] = match.group(2).strip()
    if current_values is not None:
        items.append((current_label, current_values))
    return items


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
    items = extract_legacy_results_items(body) or [("1", {})]
    for item_label, values in items:
        for key, label in REQUIRED_RESULTS_FIELDS:
            if is_blank(values.get(key)):
                findings.append(
                    Finding(
                        severity(strict),
                        f"`{rel_path}` の Results hierarchy item `{item_label}` で {label} が未記入です",
                    )
                )
    return findings


def check_typed_results_hierarchy(
    rel_path: str,
    data: dict[str, Any],
    strict: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    finding_severity = severity(strict)

    if type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        findings.append(
            Finding(
                finding_severity,
                f"`{rel_path}` の `schema_version` は 1 である必要があります",
            )
        )

    items = data.get("items")
    if not isinstance(items, list) or not items:
        findings.append(
            Finding(
                finding_severity,
                f"`{rel_path}` の `items` must be a non-empty list",
            )
        )
        return findings

    seen_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            findings.append(
                Finding(
                    finding_severity,
                    f"`{rel_path}` の Results hierarchy item `{index}` must be a mapping",
                )
            )
            continue

        raw_item_id = item.get("id")
        item_id = raw_item_id if isinstance(raw_item_id, str) else ""
        item_label = item_id or str(index)
        if is_blank(item_id) or TYPED_RESULTS_ID_RE.fullmatch(item_id) is None:
            findings.append(
                Finding(
                    finding_severity,
                    f"`{rel_path}` の Results hierarchy item id `{item_id}` must match `RHI-*` and not be a placeholder",
                )
            )
        if item_id in seen_ids:
            findings.append(
                Finding(
                    finding_severity,
                    f"`{rel_path}` has duplicate Results hierarchy item id `{item_id}`",
                )
            )
        elif item_id:
            seen_ids.add(item_id)

        for field in REQUIRED_TYPED_RESULTS_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or is_blank(value):
                findings.append(
                    Finding(
                        finding_severity,
                        f"`{rel_path}` の Results hierarchy item `{item_label}` で `{field}` が未記入です",
                    )
                )

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        raw_item_id = item.get("id")
        item_label = raw_item_id if isinstance(raw_item_id, str) and raw_item_id else str(index + 1)
        next_item_id = item.get("next_item_id")
        if index + 1 < len(items):
            next_item = items[index + 1]
            expected_id = next_item.get("id") if isinstance(next_item, dict) else None
            if next_item_id != expected_id:
                findings.append(
                    Finding(
                        finding_severity,
                        f"`{rel_path}` の Results hierarchy item `{item_label}` の next_item_id `{next_item_id}` は配列上の次 item `{expected_id}` と一致する必要があります",
                    )
                )
        elif next_item_id != "":
            findings.append(
                Finding(
                    finding_severity,
                    f"`{rel_path}` の terminal item `{item_label}` の next_item_id は空である必要があります",
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
    typed_path = resolve_results_hierarchy_path(root)
    if typed_path.exists():
        findings.extend(
            check_typed_results_hierarchy(
                display_path(root, typed_path),
                load_mapping(typed_path),
                strict,
            )
        )
    else:
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
    return emit_findings(
        "section-contract-check",
        check(root, read_text(path), rel_path, strict=args.strict),
        success_message="section contracts は Results hierarchy / Discussion functions / Methods registry を満たしています。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
