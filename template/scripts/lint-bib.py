#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


ENTRY_RE = re.compile(
    r"@(?P<entry_type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,(?P<body>.*?)\n\}",
    re.DOTALL,
)
FIELD_RE = re.compile(r"^\s*(?P<field>[A-Za-z]+)\s*=", re.MULTILINE)
DEFAULT_CITE_COMMANDS = {
    "autocite",
    "cite",
    "citealp",
    "citeauthor",
    "citep",
    "citet",
    "cites",
    "citeyear",
    "citeyearpar",
    "footcite",
    "nocite",
    "parencite",
    "parencites",
    "smartcite",
    "supercite",
    "textcite",
    "textcites",
}


def iter_bib_files(root):
    candidates = [
        root / "manuscript/shared/bib",
        root / "refs/bib/imported",
        root / "refs/bib/curated",
    ]
    files = []
    for directory in candidates:
        if directory.exists():
            files.extend(sorted(directory.glob("*.bib")))
    return files


def iter_tex_files(root: Path):
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return
    for path in sorted(manuscript.glob("**/*.tex")):
        if "shared/style" in path.as_posix():
            continue
        yield path


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        kept = []
        for char in line:
            if char == "%" and not escaped:
                break
            kept.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        lines.append("".join(kept))
    return "\n".join(lines)


def consume_optional_groups(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    while index < len(text) and text[index] == "[":
        depth = 1
        index += 1
        while index < len(text) and depth:
            if text[index] == "[":
                depth += 1
            elif text[index] == "]":
                depth -= 1
            index += 1
        while index < len(text) and text[index].isspace():
            index += 1
    return index


def consume_brace_group(text: str, index: int) -> tuple[str | None, int]:
    if index >= len(text) or text[index] != "{":
        return None, index
    depth = 1
    index += 1
    start = index
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index], index + 1
        index += 1
    return None, index


def extract_cited_keys(root: Path) -> set[str]:
    cited = set()
    command_re = re.compile(r"\\(?P<command>[A-Za-z]+)\*?")
    for tex_file in iter_tex_files(root):
        text = strip_comments(tex_file.read_text(encoding="utf-8"))
        for match in command_re.finditer(text):
            command = match.group("command")
            if command not in DEFAULT_CITE_COMMANDS:
                continue
            index = match.end()
            while True:
                index = consume_optional_groups(text, index)
                keys, index = consume_brace_group(text, index)
                if keys is None:
                    break
                for key in keys.split(","):
                    cleaned = key.strip()
                    if cleaned:
                        cited.add(cleaned)
                if not command.endswith("s"):
                    break
    return cited


def summary_matches_key(path: Path, key: str) -> bool:
    if path.stem == key:
        return True
    text = path.read_text(encoding="utf-8")
    return f"Citation key: {key}" in text or f"# {key}" in text


def has_summary(root: Path, key: str) -> bool:
    summary_dir = root / "refs" / "summaries"
    if not summary_dir.exists():
        return False
    for path in summary_dir.glob("*.md"):
        if path.name == "summary-template.md":
            continue
        if summary_matches_key(path, key):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="論文ハーネス内の参考文献ファイルを lint する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--mode",
        choices=["starter", "pre-submit"],
        default="starter",
        help="starter は空の bib を許容し、pre-submit は引用サマリーの不足をエラーにする。",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    files = iter_bib_files(root)
    if not files:
        print(".bib ファイルが見つかりません")
        return 1

    keys = {}
    errors = []
    warnings = []

    for bib_file in files:
        text = bib_file.read_text(encoding="utf-8")
        for match in ENTRY_RE.finditer(text):
            key = match.group("key").strip()
            body = match.group("body")
            if key in keys:
                errors.append(f"重複キー '{key}': {bib_file} と {keys[key]}")
            else:
                keys[key] = bib_file

            fields = {m.group("field").lower() for m in FIELD_RE.finditer(body)}
            missing = {"title", "author", "year"} - fields
            if missing:
                errors.append(
                    f"{bib_file}: エントリ '{key}' に必須フィールドが不足: {', '.join(sorted(missing))}"
                )

    cited = extract_cited_keys(root)
    if args.mode == "pre-submit":
        if not cited:
            warnings.append("本文中の citation key が見つかりません。投稿前なら引用漏れではないか確認してください")
        for key in sorted(cited):
            if key not in keys:
                errors.append(f"本文が citation key `{key}` を参照していますが .bib にありません")
            elif not has_summary(root, key):
                errors.append(f"引用 `{key}` に対応する `refs/summaries/` の検証サマリーがありません")

    if errors:
        print("参考文献の lint に失敗しました")
        for error in errors:
            print(f"- {error}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    for warning in warnings:
        print(f"警告: {warning}")
    print("参考文献の lint に成功しました: {} ファイル、{} エントリ".format(len(files), len(keys)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
