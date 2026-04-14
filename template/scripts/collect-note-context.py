#!/usr/bin/env python3

import argparse
from pathlib import Path


SECTIONS = [
    ("プロジェクト概要", "docs/project-brief.md"),
    ("セッションコンテキスト", "notes/session-context.md"),
    ("引き継ぎ", "notes/handoff.md"),
    ("Todo", "notes/todo.md"),
    ("未解決の質問", "notes/open-questions.md"),
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
