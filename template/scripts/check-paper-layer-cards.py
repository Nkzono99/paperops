#!/usr/bin/env python3

import argparse
from pathlib import Path

from paperops_checks import Finding, emit_findings, read_text
from paperops_paths import display_path, internal_path


REQUIRED_FILES = [
    "defaults/schemas/registry.yml",
    "model/research/index.yml",
    "model/editorial/editorial-model.yml",
    "model/editorial/results-hierarchy.yml",
    "model/manuscript/index.yml",
    "model/issues/index.yml",
    "model/publication/publication-model.yml",
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


FRONTMATTER_REQUIREMENTS: dict[str, list[str]] = {}


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


def check_required_files(root: Path, findings: list[Finding]) -> None:
    for rel_path in REQUIRED_FILES:
        path = internal_path(root, rel_path)
        if not path.exists():
            findings.append(Finding("error", f"`{display_path(root, path)}` が見つかりません"))


def check_frontmatter_tokens(root: Path, findings: list[Finding]) -> None:
    requirements = FRONTMATTER_REQUIREMENTS | VIEW_FRONTMATTER_REQUIREMENTS
    for rel_path, tokens in requirements.items():
        path = internal_path(root, rel_path)
        if not path.exists():
            continue
        text = read_text(path)
        for token in tokens:
            if token not in text:
                findings.append(Finding("error", f"`{display_path(root, path)}` に `{token}` がありません"))


def check_legacy_views(root: Path, findings: list[Finding]) -> None:
    for rel_path in LEGACY_VIEW_FILES:
        path = internal_path(root, rel_path)
        if not path.exists():
            findings.append(Finding("error", f"`{display_path(root, path)}` が見つかりません"))
            continue
        text = read_text(path)
        if "互換ビュー" not in text or "notes/views/" not in text:
            findings.append(
                Finding(
                    "warning",
                    f"`{display_path(root, path)}` は互換ビューとして `_paperops/notes/views/` を案内してください",
                )
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="typed model authority と互換ビューの外形を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[Finding] = []
    check_required_files(root, findings)
    check_frontmatter_tokens(root, findings)
    check_legacy_views(root, findings)

    return emit_findings(
        "paper typed layers",
        findings,
        success_message="typed model authority と互換ビューの外形に問題は見つかりませんでした。",
    )


if __name__ == "__main__":
    raise SystemExit(main())
