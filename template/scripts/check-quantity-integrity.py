#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_checks import Finding, emit_findings, read_text, warning_severity
from paperops_paths import display_path
from paperops_typed_views import indexed_documents


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
class QuantityContract:
    path: Path
    value: str
    denominator: str
    fields: dict[str, str]


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


def result_contracts(root: Path) -> list[QuantityContract]:
    contracts: list[QuantityContract] = []
    for item in indexed_documents(root, "research", "result"):
        for raw in item.document.get("quantity_contracts", []):
            if isinstance(raw, dict):
                fields = {str(key): " ".join(value) if isinstance(value, list) else str(value) for key, value in raw.items()}
                fields["source_artifact"] = fields.get("source_artifact_id", "")
                fields["manuscript_blocks"] = fields.get("manuscript_block_refs", "")
                contracts.append(make_contract(item.path, fields))
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
    contracts.extend(result_contracts(root))

    for contract in contracts:
        for field in REQUIRED_FIELDS:
            if is_blank(contract.fields.get(field)):
                findings.append(
                    Finding(
                        warning_severity(strict),
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
                    warning_severity(strict),
                    f"未登録の数量表現 `{value} of {denominator}` が manuscript にあります。"
                    "typed Research result の quantity_contracts に value / denominator / unit_of_analysis を登録してください。",
                )
            )
    if strict and seen_pairs and not contracts:
        findings.append(
            Finding(
                "error",
                "manuscript に count fraction がありますが typed Research result に quantity_contracts がありません",
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
    return emit_findings(
        "quantity-integrity-check",
        findings,
        success_message="quantity integrity の未登録 count fraction は見つかりませんでした。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
