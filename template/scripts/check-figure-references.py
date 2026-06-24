#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


FIGURE_ENV_RE = re.compile(
    r"\\begin\{figure\*?\}(?P<body>.*?)\\end\{figure\*?\}",
    re.DOTALL,
)
LABEL_RE = re.compile(r"\\label\{(?P<label>fig:[^}]+)\}")
REF_RE = re.compile(
    r"\\(?:ref|autoref|cref|Cref|figref|Figref)\{(?P<labels>[^}]+)\}"
)


@dataclass(frozen=True)
class FigureLabel:
    label: str
    path: Path
    line: int


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_unescaped_comment(line: str) -> str:
    escaped = False
    for index, char in enumerate(line):
        if char == "\\":
            escaped = not escaped
            continue
        if char == "%" and not escaped:
            return line[:index]
        escaped = False
    return line


def uncomment(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            lines.append("")
        else:
            lines.append(strip_unescaped_comment(line))
    return "\n".join(lines)


def manuscript_tex_files(root: Path) -> list[Path]:
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return []
    return [
        path
        for path in sorted(manuscript.glob("**/*.tex"))
        if "shared/style" not in path.as_posix()
    ]


def language_for(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    if "ja" in parts:
        return "ja"
    if "en" in parts:
        return "en"
    return "unknown"


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def collect_labels_and_refs(root: Path) -> tuple[dict[str, list[FigureLabel]], dict[str, set[str]]]:
    labels_by_lang: dict[str, list[FigureLabel]] = {}
    refs_by_lang: dict[str, set[str]] = {}
    for path in manuscript_tex_files(root):
        raw = read_text(path)
        text = uncomment(raw)
        lang = language_for(path, root)

        figure_ranges: list[tuple[int, int]] = []
        for figure in FIGURE_ENV_RE.finditer(text):
            figure_ranges.append((figure.start(), figure.end()))
            for label_match in LABEL_RE.finditer(figure.group("body")):
                absolute_offset = figure.start("body") + label_match.start()
                labels_by_lang.setdefault(lang, []).append(
                    FigureLabel(
                        label=label_match.group("label").strip(),
                        path=path,
                        line=line_number(text, absolute_offset),
                    )
                )

        body_parts: list[str] = []
        cursor = 0
        for start, end in figure_ranges:
            body_parts.append(text[cursor:start])
            cursor = end
        body_parts.append(text[cursor:])
        body_without_figures = "\n".join(body_parts)
        for ref_match in REF_RE.finditer(body_without_figures):
            for label in ref_match.group("labels").split(","):
                normalized = label.strip()
                if normalized.startswith("fig:"):
                    refs_by_lang.setdefault(lang, set()).add(normalized)

    return labels_by_lang, refs_by_lang


def check_figure_references(root: Path) -> list[Finding]:
    labels_by_lang, refs_by_lang = collect_labels_and_refs(root)
    findings: list[Finding] = []
    for lang, labels in sorted(labels_by_lang.items()):
        refs = refs_by_lang.get(lang, set())
        seen: set[tuple[str, str]] = set()
        for figure_label in labels:
            key = (lang, figure_label.label)
            if key in seen:
                continue
            seen.add(key)
            if figure_label.label in refs:
                continue
            rel_path = figure_label.path.relative_to(root).as_posix()
            findings.append(
                Finding(
                    "warning",
                    f"`{rel_path}:{figure_label.line}` の `{figure_label.label}` は本文参照がありません。"
                    " main-text figure は図環境外の本文で `\\ref{...}` / `\\autoref{...}` / `\\cref{...}` から narrative に接続してください。",
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="main-text figure label が本文から参照されているか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="warning がある場合も non-zero exit を返す。")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check_figure_references(root)

    print("# figure-reference-check")
    print("")
    if findings:
        print("## Warnings")
        for finding in findings:
            print(f"- {finding.message}")
        print("")
        print("figure card、caption、本文の claim route を確認し、図が本文の論旨に接続されている状態にしてください。")
    else:
        print("main-text figure label の本文参照に明らかな問題は見つかりませんでした。")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
