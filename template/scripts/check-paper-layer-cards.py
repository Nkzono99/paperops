#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    severity: str
    message: str


REQUIRED_FILES = [
    "evidence/README.md",
    "evidence/results/result-card-template.md",
    "evidence/figures/figure-card-template.md",
    "evidence/sources/source-card-template.md",
    "claims/README.md",
    "claims/claims/claim-card-template.md",
    "claims/gates/scientific-gate-card-template.md",
    "claims/arguments/argument-card-template.md",
    "review/README.md",
    "review/feedback/feedback-card-template.md",
    "review/rounds/review-round-template.md",
    "review/responses/response-card-template.md",
    "requests/README.md",
    "requests/analysis/analysis-request-template.md",
    "requests/writing/writing-request-template.md",
    "notes/views/README.md",
    "notes/views/result-pattern-map.md",
    "notes/views/claim-evidence-map.md",
    "notes/views/scientific-gate.md",
    "notes/views/argument-map.md",
    "notes/views/concept-terms.md",
    "notes/views/condition-context-map.md",
    "notes/views/assumption-ledger.md",
    "notes/views/claim-upgrade-gates.md",
    "notes/views/peer-review.md",
    "notes/views/research-requests.md",
]


FRONTMATTER_REQUIREMENTS = {
    "evidence/results/result-card-template.md": ["---", "type: result", "claim_links:"],
    "evidence/figures/figure-card-template.md": [
        "---",
        "type: figure",
        "supports_claims:",
        "satisfies_visual_obligations:",
    ],
    "evidence/sources/source-card-template.md": ["---", "type: source", "source_kind:"],
    "claims/claims/claim-card-template.md": [
        "---",
        "type: claim",
        "depends_on:",
        "visual_obligations:",
        "no_figure_reason:",
    ],
    "claims/gates/scientific-gate-card-template.md": ["---", "type: scientific_gate", "gate_status:"],
    "claims/arguments/argument-card-template.md": ["---", "type: argument", "claim_order:"],
    "review/feedback/feedback-card-template.md": ["---", "type: feedback", "target:", "upstream_routes:"],
    "review/rounds/review-round-template.md": ["---", "type: review_round", "feedback_cards:"],
    "review/responses/response-card-template.md": ["---", "type: response", "feedback_cards:"],
    "requests/analysis/analysis-request-template.md": ["---", "type: analysis_request", "requested_outputs:"],
    "requests/writing/writing-request-template.md": ["---", "type: writing_request", "target_blocks:"],
}


VIEW_FRONTMATTER_REQUIREMENTS = {
    "notes/views/result-pattern-map.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/claim-evidence-map.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/scientific-gate.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/peer-review.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/research-requests.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/assumption-ledger.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/claim-upgrade-gates.md": ["---", "view_type: pure_overview", "source_of_truth:"],
    "notes/views/argument-map.md": ["---", "view_type: controlled_authoring", "source_of_truth:"],
    "notes/views/concept-terms.md": ["---", "view_type: controlled_authoring", "source_of_truth:"],
    "notes/views/condition-context-map.md": ["---", "view_type: controlled_authoring", "source_of_truth:"],
}


LEGACY_VIEW_FILES = [
    "notes/result-pattern-map.md",
    "notes/claim-evidence-map.md",
    "notes/scientific-gate.md",
    "notes/argument-map.md",
    "notes/condition-context-map.md",
    "notes/assumption-ledger.md",
    "notes/claim-upgrade-gates.md",
    "notes/peer-review.md",
    "notes/research-requests.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_required_files(root: Path, findings: list[Finding]) -> None:
    for rel_path in REQUIRED_FILES:
        path = root / rel_path
        if not path.exists():
            findings.append(Finding("error", f"`{rel_path}` が見つかりません"))


def check_frontmatter_tokens(root: Path, findings: list[Finding]) -> None:
    requirements = FRONTMATTER_REQUIREMENTS | VIEW_FRONTMATTER_REQUIREMENTS
    for rel_path, tokens in requirements.items():
        path = root / rel_path
        if not path.exists():
            continue
        text = read_text(path)
        for token in tokens:
            if token not in text:
                findings.append(Finding("error", f"`{rel_path}` に `{token}` がありません"))


def check_legacy_views(root: Path, findings: list[Finding]) -> None:
    for rel_path in LEGACY_VIEW_FILES:
        path = root / rel_path
        if not path.exists():
            findings.append(Finding("error", f"`{rel_path}` が見つかりません"))
            continue
        text = read_text(path)
        if "互換ビュー" not in text or "notes/views/" not in text:
            findings.append(
                Finding(
                    "warning",
                    f"`{rel_path}` は互換ビューとして `notes/views/` を案内してください",
                )
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="論文執筆カード層と互換ビューの外形を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[Finding] = []
    check_required_files(root, findings)
    check_frontmatter_tokens(root, findings)
    check_legacy_views(root, findings)

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# paper layer cards")
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
        print("カード層と互換ビューの外形に問題は見つかりませんでした。")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
