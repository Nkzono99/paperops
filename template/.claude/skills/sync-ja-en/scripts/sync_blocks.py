#!/usr/bin/env python3

import argparse
import re
from pathlib import Path
from typing import List


BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(?P<block_id>[A-Za-z0-9_.-]+)\s*$")


def extract_blocks(path):
    blocks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = BLOCK_RE.match(line)
        if match:
            blocks.append(match.group("block_id"))
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare block IDs between two section files.")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    source_blocks = extract_blocks(args.source)
    target_blocks = extract_blocks(args.target)

    missing_in_target = [block for block in source_blocks if block not in target_blocks]
    missing_in_source = [block for block in target_blocks if block not in source_blocks]

    print(f"source: {args.source}")
    print(f"target: {args.target}")
    print(f"source_blocks: {len(source_blocks)}")
    print(f"target_blocks: {len(target_blocks)}")

    if missing_in_target:
        print("missing_in_target:")
        for block in missing_in_target:
            print("  - {}".format(block))

    if missing_in_source:
        print("missing_in_source:")
        for block in missing_in_source:
            print("  - {}".format(block))

    return 1 if missing_in_target or missing_in_source else 0


if __name__ == "__main__":
    raise SystemExit(main())
