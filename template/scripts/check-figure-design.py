#!/usr/bin/env python3
"""Check that manuscript-facing figure cards carry a usable design review."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from paperops_checks import (
    Finding,
    emit_findings,
    field_values,
    frontmatter,
    meaningful_value,
    nested_scalar,
    read_text,
    scalar_value,
    warning_severity,
)
from paperops_paths import display_path, internal_path


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


def meaningful(value: str) -> bool:
    return meaningful_value(value)


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
