#!/usr/bin/env python3
"""Check that manuscript-facing figure cards carry a usable design review."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_checks import Finding, emit_findings, frontmatter, read_text, warning_severity
from paperops_paths import display_path, internal_path


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
SKIP_ROLES = {"notes-only", "removed", "discarded"}
SKIP_STATUSES = {"removed", "discarded"}
DESIGN_REVIEW_FIELDS = (
    "reader_task",
    "takeaway_sentence",
    "claim_or_decision",
    "encoding_choice",
    "scale_and_denominator",
    "uncertainty_or_distribution",
    "annotation_caption",
    "color_accessibility",
    "runops_handoff",
    "acceptance_criteria",
)
CONNECTION_FIELDS = (
    "supports_claims",
    "uses_results",
    "manuscript_blocks",
    "satisfies_visual_obligations",
)


@dataclass(frozen=True)
class FigureCard:
    figure_id: str
    path: Path
    front: str
    status: str
    manuscript_role: str


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


def scalar_value(front: str, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(front)
    if not match:
        return ""
    return clean_value(match.group(1))


def nested_scalar(front: str, parent: str, key: str) -> str:
    block = field_block(front, parent)
    pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return ""
    return clean_value(match.group(1))


def clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def meaningful(value: str) -> bool:
    return clean_value(value).strip().lower() not in PLACEHOLDER_VALUES


def field_values(front: str, key: str) -> list[str]:
    block = field_block(front, key)
    if not block:
        return []
    first = block.splitlines()[0]
    inline = clean_value(first.split(":", 1)[1])
    if inline.startswith("[") and inline.endswith("]"):
        return [
            clean_value(item)
            for item in inline[1:-1].split(",")
            if meaningful(item)
        ]
    if meaningful(inline):
        return [inline]
    values: list[str] = []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        item = clean_value(stripped[1:])
        if meaningful(item):
            values.append(item)
    return values


def figure_cards(root: Path) -> list[FigureCard]:
    base = internal_path(root, "evidence", "figures")
    if not base.exists():
        return []
    cards: list[FigureCard] = []
    for path in sorted(base.glob("*.md")):
        if path.name.endswith("-template.md") or path.name == "README.md":
            continue
        front = frontmatter(read_text(path))
        if not front:
            continue
        cards.append(
            FigureCard(
                figure_id=scalar_value(front, "id") or path.stem,
                path=path,
                front=front,
                status=scalar_value(front, "status").lower(),
                manuscript_role=scalar_value(front, "current_manuscript_role").lower(),
            )
        )
    return cards


def should_review(card: FigureCard) -> bool:
    if card.status in SKIP_STATUSES or card.manuscript_role in SKIP_ROLES:
        return False
    if card.manuscript_role == "main":
        return True
    return any(field_values(card.front, field) for field in CONNECTION_FIELDS)


def check(root: Path, strict: bool) -> list[Finding]:
    severity = warning_severity(strict)
    findings: list[Finding] = []
    for card in figure_cards(root):
        if not should_review(card):
            continue
        missing: list[str] = []
        if not meaningful(scalar_value(card.front, "figure_ref")):
            missing.append("figure_ref")
        if not any(field_values(card.front, field) for field in CONNECTION_FIELDS):
            missing.append("supports_claims / uses_results / manuscript_blocks / satisfies_visual_obligations")
        for field in DESIGN_REVIEW_FIELDS:
            if not meaningful(nested_scalar(card.front, "design_review", field)):
                missing.append(f"design_review.{field}")
        if missing:
            findings.append(
                Finding(
                    severity,
                    f"`{display_path(root, card.path)}` ({card.figure_id}) の figure design review が未完了です: "
                    + ", ".join(missing),
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="main / claim-facing figure card の design review が埋まっているか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    return emit_findings(
        "figure-design-check",
        check(root, strict=args.strict),
        success_message="figure design review に問題は見つかりませんでした。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
