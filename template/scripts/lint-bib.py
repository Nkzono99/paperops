#!/usr/bin/env python3

import argparse
import re
from pathlib import Path
from typing import Dict, List


ENTRY_RE = re.compile(
    r"@(?P<entry_type>[A-Za-z]+)\s*\{\s*(?P<key>[^,\s]+)\s*,(?P<body>.*?)\n\}",
    re.DOTALL,
)
FIELD_RE = re.compile(r"^\s*(?P<field>[A-Za-z]+)\s*=", re.MULTILINE)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint bibliography files in the paper harness.")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    files = iter_bib_files(root)
    if not files:
        print("no .bib files found")
        return 1

    keys = {}
    errors = []

    for bib_file in files:
        text = bib_file.read_text(encoding="utf-8")
        for match in ENTRY_RE.finditer(text):
            key = match.group("key").strip()
            body = match.group("body")
            if key in keys:
                errors.append(f"duplicate key '{key}' in {bib_file} and {keys[key]}")
            else:
                keys[key] = bib_file

            fields = {m.group("field").lower() for m in FIELD_RE.finditer(body)}
            missing = {"title", "author", "year"} - fields
            if missing:
                errors.append(
                    f"{bib_file}: entry '{key}' missing required fields: {', '.join(sorted(missing))}"
                )

    if errors:
        print("bibliography lint failed")
        for error in errors:
            print(f"- {error}")
        return 1

        print("bibliography lint passed for {} file(s) and {} entries".format(len(files), len(keys)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
