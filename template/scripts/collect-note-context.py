#!/usr/bin/env python3

import argparse
from pathlib import Path


SECTIONS = [
    ("プロジェクト概要", "notes/project-brief.md"),
    ("科学的ゲート", "notes/scientific-gate.md"),
    ("結果パターン", "notes/result-pattern-map.md"),
    ("主張と証拠", "notes/claim-evidence-map.md"),
    ("論旨設計", "notes/argument-map.md"),
    ("関連研究", "notes/related-work-map.md"),
    ("外部ソース到達", "notes/source-reach.md"),
    ("条件文脈", "notes/condition-context-map.md"),
    ("読者モデル", "notes/reviewer-model.md"),
    ("査読・返答", "notes/peer-review.md"),
    ("AI 初稿 polish", "notes/ai-draft-polish.md"),
    ("AI 利用", "notes/ai-use.md"),
    ("引き継ぎ", "notes/handoff.md"),
    ("Todo", "notes/todo.md"),
    ("未解決の質問", "notes/open-questions.md"),
    ("追加解析・図表・実験要望", "notes/research-requests.md"),
    ("再現性", "notes/reproducibility.md"),
]


def read_section(root, rel_path):
    path = root / rel_path
    if not path.exists():
        return "_不存在_"
    return path.read_text(encoding="utf-8").strip()


def render_context(root):
    lines = ["# セッションコンテキストスナップショット", ""]
    for title, rel_path in SECTIONS:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(read_section(root, rel_path))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="セッション開始用のコアノートコンテキストを収集する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    rendered = render_context(root)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
