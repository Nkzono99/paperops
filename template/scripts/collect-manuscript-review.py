#!/usr/bin/env python3

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


MARKER_RE = re.compile(r"(?<!\\)%\s*(REVIEW|AI|Q|KEEP\?|TODO-PAPER)\s*:?\s*(.*)$")
BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(\S+)")
MANUSCRIPT_DIRS = ("manuscript/ja", "manuscript/en")


@dataclass
class InlineComment:
    rel_path: str
    line_number: int
    block_id: str
    marker: str
    body: str


@dataclass
class DiffHunk:
    rel_path: str
    header: str
    added: int
    removed: int
    excerpts: list[str]


def run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def collect_inline_comments(root: Path) -> list[InlineComment]:
    comments: list[InlineComment] = []
    for manuscript_dir in MANUSCRIPT_DIRS:
        base = root / manuscript_dir
        if not base.exists():
            continue
        for path in sorted(base.glob("**/*.tex")):
            current_block = "unknown"
            rel_path = path.relative_to(root).as_posix()
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                block_match = BLOCK_RE.match(line)
                if block_match:
                    current_block = block_match.group(1)
                marker_match = MARKER_RE.search(line)
                if marker_match:
                    comments.append(
                        InlineComment(
                            rel_path=rel_path,
                            line_number=line_number,
                            block_id=current_block,
                            marker=marker_match.group(1),
                            body=marker_match.group(2).strip(),
                        )
                    )
    return comments


def trim_excerpt(line: str, limit: int = 160) -> str:
    text = line[1:].strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return f"{line[0]} {text}"


def flush_hunk(hunks: list[DiffHunk], current: dict[str, object] | None) -> None:
    if not current:
        return
    hunks.append(
        DiffHunk(
            rel_path=str(current["rel_path"]),
            header=str(current["header"]),
            added=int(current["added"]),
            removed=int(current["removed"]),
            excerpts=list(current["excerpts"]),
        )
    )


def collect_diff_hunks(root: Path) -> list[DiffHunk]:
    diff = run_git(root, "diff", "--", *MANUSCRIPT_DIRS)
    hunks: list[DiffHunk] = []
    current_path = ""
    current_hunk: dict[str, object] | None = None

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush_hunk(hunks, current_hunk)
            current_hunk = None
            parts = line.split(" b/", 1)
            current_path = parts[1] if len(parts) == 2 else ""
            continue
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/")
            continue
        if line.startswith("@@ "):
            flush_hunk(hunks, current_hunk)
            current_hunk = {
                "rel_path": current_path,
                "header": line,
                "added": 0,
                "removed": 0,
                "excerpts": [],
            }
            continue
        if current_hunk is None or line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            current_hunk["added"] = int(current_hunk["added"]) + 1
            excerpts = current_hunk["excerpts"]
            if isinstance(excerpts, list) and len(excerpts) < 8:
                excerpts.append(trim_excerpt(line))
        elif line.startswith("-"):
            current_hunk["removed"] = int(current_hunk["removed"]) + 1
            excerpts = current_hunk["excerpts"]
            if isinstance(excerpts, list) and len(excerpts) < 8:
                excerpts.append(trim_excerpt(line))

    flush_hunk(hunks, current_hunk)
    return hunks


def render_comments(comments: list[InlineComment]) -> list[str]:
    if not comments:
        return ["_inline review comment は見つかりませんでした。_", ""]

    lines = [
        "| file | line | block | marker | comment |",
        "|---|---:|---|---|---|",
    ]
    for comment in comments:
        body = comment.body.replace("|", "\\|")
        lines.append(
            f"| `{comment.rel_path}` | {comment.line_number} | `{comment.block_id}` | `{comment.marker}` | {body} |"
        )
    lines.append("")
    return lines


def render_diff_hunks(hunks: list[DiffHunk]) -> list[str]:
    if not hunks:
        return ["_manuscript/ja または manuscript/en の git diff は見つかりませんでした。_", ""]

    lines: list[str] = []
    for hunk in hunks:
        lines.append(f"### `{hunk.rel_path}`")
        lines.append("")
        lines.append(f"- hunk: `{hunk.header}`")
        lines.append(f"- added: {hunk.added}")
        lines.append(f"- removed: {hunk.removed}")
        if hunk.excerpts:
            lines.append("- excerpt:")
            lines.append("")
            lines.append("```diff")
            lines.extend(hunk.excerpts)
            lines.append("```")
        lines.append("")
    return lines


def render_report(root: Path, review_date: str) -> str:
    comments = collect_inline_comments(root)
    hunks = collect_diff_hunks(root)
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"

    lines = [
        f"# Manuscript review intake - {review_date}",
        "",
        "## 対象",
        "",
        f"- branch: `{branch}`",
        "- diff scope: `manuscript/ja`, `manuscript/en`",
        "- inline markers: `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% TODO-PAPER:`",
        "",
        "## Inline comments",
        "",
    ]
    lines.extend(render_comments(comments))
    lines.extend(
        [
            "## Direct edit diff",
            "",
        ]
    )
    lines.extend(render_diff_hunks(hunks))
    lines.extend(
        [
            "## 編集傾向メモ",
            "",
            "- [ ] 直接編集 diff から、人間が好む表現・削った説明・強めた主張を要約する。",
            "- [ ] 単なる文言修正と、科学的意味が変わる修正を分ける。",
            "",
            "## 反映方針",
            "",
            "- [ ] source-of-truth 側の TeX に反映する項目を決める。",
            "- [ ] 解決済み inline comment を削除し、未解決の論点はこの台帳または `_paperops/notes/todo.md` に残す。",
            "- [ ] `manuscript/en` へ同期が必要な block ID を列挙する。",
            "",
            "## Open questions",
            "",
            "- [ ] 人間の判断が必要な科学的主張、構成変更、削除候補を列挙する。",
            "",
            "## Apply log",
            "",
            "- [ ] 反映後に `make mirror-check` を実行する。",
            "- [ ] 構造、引用、refs に触れた場合は `make ci` を実行する。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TeX の inline review comment と manuscript diff からレビュー台帳を生成する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    report = render_report(root, args.date)

    if args.output is not None:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")

    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
