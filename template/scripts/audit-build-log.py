#!/usr/bin/env python3
"""Audit LaTeX build logs for failures that are easy to miss."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pattern:
    label: str
    regex: re.Pattern[str]


ERROR_PATTERNS = [
    Pattern("LaTeX error", re.compile(r"^! (?:LaTeX|Package|Class) Error:", re.MULTILINE)),
    Pattern("fatal TeX stop", re.compile(r"(Fatal error occurred|Emergency stop|Undefined control sequence)", re.I)),
    Pattern("undefined citation/reference", re.compile(r"(Citation .* undefined|Reference .* undefined|undefined references|undefined citations)", re.I)),
    Pattern("Missing character", re.compile(r"Missing character:", re.I)),
    Pattern("BibTeX database error", re.compile(r"(I couldn't open database file|Database file .* not found|bibdata command)", re.I)),
    Pattern("empty bibliography", re.compile(r"(Empty `?thebibliography'? environment|No file .*\.bbl)", re.I)),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="LaTeX build log の fatal / citation / font 問題を確認する。")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--label", default="PDF build")
    args = parser.parse_args()

    print("# build-log-audit")
    print("")

    if not args.log.exists():
        print("## Errors")
        print(f"- {args.label}: build log `{args.log}` が見つかりません")
        return 1

    text = args.log.read_text(encoding="utf-8", errors="replace")
    findings = []
    for pattern in ERROR_PATTERNS:
        if pattern.regex.search(text):
            findings.append(pattern.label)

    if findings:
        print("## Errors")
        for finding in findings:
            print(f"- {args.label}: {finding}")
        return 1

    print(f"{args.label}: build log に fatal な問題は見つかりませんでした。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
