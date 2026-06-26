#!/usr/bin/env python3

import argparse
import re
from pathlib import Path

from paperops_paths import internal_path


BIB_ENTRY_RE = re.compile(r"@(?P<entry_type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,", re.DOTALL)
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


def iter_bib_files(root: Path):
    candidates = [
        root / "manuscript/shared/bib",
        internal_path(root, "refs/bib/imported"),
        internal_path(root, "refs/bib/curated"),
    ]
    for directory in candidates:
        if directory.exists():
            yield from sorted(directory.glob("*.bib"))


def iter_tex_files(root: Path):
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return
    for path in sorted(manuscript.glob("**/*.tex")):
        if "shared/style" in path.as_posix():
            continue
        yield path


def load_bib_keys(root: Path) -> set[str]:
    keys = set()
    for bib_file in iter_bib_files(root):
        text = bib_file.read_text(encoding="utf-8")
        for match in BIB_ENTRY_RE.finditer(text):
            keys.add(match.group("key").strip())
    return keys


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


def extract_citations(path: Path, commands: set[str]):
    text = strip_comments(path.read_text(encoding="utf-8"))
    command_re = re.compile(r"\\(?P<command>[A-Za-z]+)\*?")
    for match in command_re.finditer(text):
        command = match.group("command")
        if command not in commands:
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
                    yield cleaned
            if not command.endswith("s"):
                break


def main() -> int:
    parser = argparse.ArgumentParser(description="TeX 原稿中の citation key が .bib に存在するか確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--extra-command",
        action="append",
        default=[],
        help="追加で citation command として扱う TeX command 名。複数指定可。",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    commands = DEFAULT_CITE_COMMANDS | set(args.extra_command)
    bib_keys = load_bib_keys(root)
    missing = []
    cited = set()

    for tex_file in iter_tex_files(root):
        rel_path = tex_file.relative_to(root).as_posix()
        for key in extract_citations(tex_file, commands):
            cited.add(key)
            if key not in bib_keys:
                missing.append(f"`{rel_path}` が未定義の citation key `{key}` を参照しています")

    if missing:
        print("citation-check に失敗しました")
        for item in missing:
            print(f"- {item}")
        return 1

    print("citation-check に成功しました: {} citation key、{} bib key".format(len(cited), len(bib_keys)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
