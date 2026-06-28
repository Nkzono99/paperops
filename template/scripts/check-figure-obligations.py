#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_checks import Finding, emit_findings, frontmatter, read_text
from paperops_paths import display_path, internal_path


OBLIGATION_RE = re.compile(r"\bVO-[A-Za-z0-9_.-]+\b")


@dataclass
class ClaimCard:
    claim_id: str
    path: Path
    status: str
    gate_status: str
    obligations: set[str]
    no_figure_reason: str


@dataclass
class FigureCard:
    figure_id: str
    path: Path
    status: str
    manuscript_role: str
    obligations: set[str]


def scalar_value(front: str, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$", re.MULTILINE)
    match = pattern.search(front)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def block(front: str, key: str) -> str:
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


def obligation_ids(front: str, key: str) -> set[str]:
    return set(OBLIGATION_RE.findall(block(front, key)))


def meaningful_reason(value: str) -> bool:
    if not value:
        return False
    return value not in {"[]", "{}", '""', "''", "未記入", "none", "None"}


def claim_cards(root: Path) -> list[ClaimCard]:
    cards: list[ClaimCard] = []
    for path in sorted(internal_path(root, "claims", "claims").glob("*.md")):
        if path.name.endswith("-template.md"):
            continue
        front = frontmatter(read_text(path))
        if not front:
            continue
        cards.append(
            ClaimCard(
                claim_id=scalar_value(front, "id") or path.stem,
                path=path,
                status=scalar_value(front, "status"),
                gate_status=scalar_value(front, "gate_status"),
                obligations=obligation_ids(front, "visual_obligations"),
                no_figure_reason=scalar_value(front, "no_figure_reason"),
            )
        )
    return cards


def figure_cards(root: Path) -> list[FigureCard]:
    cards: list[FigureCard] = []
    for path in sorted(internal_path(root, "evidence", "figures").glob("*.md")):
        if path.name.endswith("-template.md"):
            continue
        front = frontmatter(read_text(path))
        if not front:
            continue
        obligations = obligation_ids(front, "satisfies_visual_obligations")
        obligations |= obligation_ids(front, "visual_obligations")
        cards.append(
            FigureCard(
                figure_id=scalar_value(front, "id") or path.stem,
                path=path,
                status=scalar_value(front, "status"),
                manuscript_role=scalar_value(front, "current_manuscript_role"),
                obligations=obligations,
            )
        )
    return cards


def rel(path: Path, root: Path) -> str:
    return display_path(root, path)


def check(root: Path, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    claims = claim_cards(root)
    figures = figure_cards(root)
    satisfied: dict[str, list[FigureCard]] = {}
    for figure in figures:
        if figure.status == "removed" or figure.manuscript_role == "removed":
            continue
        for obligation_id in figure.obligations:
            satisfied.setdefault(obligation_id, []).append(figure)

    for claim in claims:
        if claim.obligations:
            for obligation_id in sorted(claim.obligations):
                if obligation_id not in satisfied:
                    findings.append(
                        Finding(
                            "error",
                            f"`{rel(claim.path, root)}` の figure obligation `{obligation_id}` は、"
                            "`_paperops/evidence/figures/` の `satisfies_visual_obligations` から満たされていません。",
                        )
                    )
        elif strict and (
            claim.status == "supported" or claim.gate_status in {"ready-to-write", "ready"}
        ):
            if not meaningful_reason(claim.no_figure_reason):
                findings.append(
                    Finding(
                        "error",
                        f"`{rel(claim.path, root)}` ({claim.claim_id}) は supported / ready claim ですが、"
                        "`visual_obligations` または `no_figure_reason` がありません。",
                    )
                )

    if not claims:
        findings.append(
            Finding(
                "warning",
                "`_paperops/claims/claims/` に claim card がありません。figure obligation は claim 作成後に確認してください。",
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="claim の visual obligation が figure card で満たされているか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    return emit_findings(
        "figure-obligation-check",
        check(root, strict=args.strict),
        success_message="visual obligation の未接続は見つかりませんでした。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
