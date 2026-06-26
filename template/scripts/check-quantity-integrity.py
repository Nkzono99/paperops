#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import display_path, internal_path


PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|置き換えてください)")
COUNT_OF_RE = re.compile(r"\b(\d+)\s+of\s+(\d+)\b")
REQUIRED_FIELDS = [
    "value",
    "denominator",
    "unit_of_analysis",
    "estimand",
    "aggregation",
    "independence",
    "source_artifact",
    "manuscript_blocks",
]


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class QuantityContract:
    path: Path
    value: str
    denominator: str
    fields: dict[str, str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


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


def result_cards(root: Path) -> list[Path]:
    result_dir = internal_path(root, "evidence", "results")
    if not result_dir.exists():
        return []
    return [
        path
        for path in sorted(result_dir.glob("*.md"))
        if not path.name.endswith("-template.md")
    ]


def extract_quantity_contracts(path: Path) -> list[QuantityContract]:
    front = frontmatter(read_text(path))
    if not front or "quantity_contracts:" not in front:
        return []
    contracts: list[QuantityContract] = []
    current: dict[str, str] | None = None
    in_contracts = False
    current_key = ""
    for line in front.splitlines():
        if re.match(r"^quantity_contracts:\s*", line):
            in_contracts = True
            continue
        if in_contracts and line and not line.startswith((" ", "-")):
            break
        if not in_contracts:
            continue
        item_match = re.match(r"^\s*-\s+([A-Za-z0-9_/-]+):\s*(.*)$", line)
        if item_match:
            if current is not None:
                contracts.append(make_contract(path, current))
            current = {item_match.group(1): item_match.group(2).strip().strip('"').strip("'")}
            current_key = item_match.group(1)
            continue
        field_match = re.match(r"^\s+([A-Za-z0-9_/-]+):\s*(.*)$", line)
        if field_match and current is not None:
            current_key = field_match.group(1)
            current[current_key] = field_match.group(2).strip().strip('"').strip("'")
            continue
        list_match = re.match(r"^\s+-\s*(.*)$", line)
        if list_match and current is not None and current_key:
            current[current_key] = (current.get(current_key, "") + " " + list_match.group(1).strip()).strip()
    if current is not None:
        contracts.append(make_contract(path, current))
    return contracts


def make_contract(path: Path, fields: dict[str, str]) -> QuantityContract:
    return QuantityContract(
        path=path,
        value=fields.get("value", ""),
        denominator=fields.get("denominator", ""),
        fields=fields,
    )


def public_manuscript_text(root: Path) -> str:
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return ""
    chunks: list[str] = []
    for path in sorted(manuscript.rglob("*.tex")):
        chunks.append(read_text(path))
    return "\n".join(chunks)


def rel(path: Path, root: Path) -> str:
    return display_path(root, path)


def check(root: Path, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    contracts: list[QuantityContract] = []
    for path in result_cards(root):
        contracts.extend(extract_quantity_contracts(path))

    for contract in contracts:
        for field in REQUIRED_FIELDS:
            if is_blank(contract.fields.get(field)):
                findings.append(
                    Finding(
                        "error" if strict else "warning",
                        f"`{rel(contract.path, root)}` の quantity_contract `{field}` が未記入です",
                    )
                )

    declared_pairs = {
        (contract.value.strip(), contract.denominator.strip())
        for contract in contracts
        if not is_blank(contract.value) and not is_blank(contract.denominator)
    }
    seen_pairs = sorted(set(COUNT_OF_RE.findall(public_manuscript_text(root))))
    for value, denominator in seen_pairs:
        if (value, denominator) not in declared_pairs:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    f"未登録の数量表現 `{value} of {denominator}` が manuscript にあります。"
                    "`_paperops/evidence/results/` の quantity_contracts に value / denominator / unit_of_analysis を登録してください。",
                )
            )
    if strict and seen_pairs and not contracts:
        findings.append(
            Finding(
                "error",
                "manuscript に count fraction がありますが `_paperops/evidence/results/` に quantity_contracts がありません",
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="本文の数量表現と result card の quantity contract を照合する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(root, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# quantity-integrity-check")
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
        print("quantity integrity の未登録 count fraction は見つかりませんでした。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
