#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


BIB_ENTRY_RE = re.compile(r"@(?P<entry_type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,", re.DOTALL)
CITE_RE = re.compile(
    r"\\(?P<command>cite|citet|citep|citealp|citeauthor|citeyear|nocite)\s*(?:\[[^\]]*\]\s*)*\{(?P<keys>[^}]+)\}"
)


def iter_bib_files(root: Path):
    candidates = [
        root / "manuscript/shared/bib",
        root / "refs/bib/imported",
        root / "refs/bib/curated",
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


def extract_citations(path: Path):
    text = path.read_text(encoding="utf-8")
    for match in CITE_RE.finditer(text):
        for key in match.group("keys").split(","):
            cleaned = key.strip()
            if cleaned:
                yield cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description="TeX 原稿中の citation key が .bib に存在するか確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    bib_keys = load_bib_keys(root)
    missing = []
    cited = set()

    for tex_file in iter_tex_files(root):
        rel_path = tex_file.relative_to(root).as_posix()
        for key in extract_citations(tex_file):
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
