#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(?P<block_id>[A-Za-z0-9_.-]+)\s*$")
PAIR_HEADER_RE = re.compile(r"^\s*\[\[file_pair\]\]\s*$")
ASSIGN_RE = re.compile(r'^\s*(?P<key>ja|en)\s*=\s*"(?P<value>[^"]+)"\s*$')


def resolve_manuscript_root(root):
    if (root / "mirror" / "map.toml").exists():
        return root
    if (root / "manuscript" / "mirror" / "map.toml").exists():
        return root / "manuscript"
    raise FileNotFoundError(f"Could not locate manuscript/mirror/map.toml under {root}")


def extract_blocks(path):
    blocks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = BLOCK_RE.match(line)
        if match:
            blocks.append(match.group("block_id"))
    return blocks


def load_file_pairs(map_path):
    pairs = []
    current = {}

    for line in map_path.read_text(encoding="utf-8").splitlines():
        if PAIR_HEADER_RE.match(line):
            if current:
                if "ja" in current and "en" in current:
                    pairs.append((current["ja"], current["en"]))
                current = {}
            continue

        match = ASSIGN_RE.match(line)
        if match:
            current[match.group("key")] = match.group("value")

    if current and "ja" in current and "en" in current:
        pairs.append((current["ja"], current["en"]))

    return pairs


def build_report(manuscript_root):
    file_pairs = load_file_pairs(manuscript_root / "mirror" / "map.toml")

    failures = []
    rows = []

    for ja_rel, en_rel in file_pairs:
        ja_path = manuscript_root / ja_rel
        en_path = manuscript_root / en_rel

        if not ja_path.exists() or not en_path.exists():
            failures.append(f"missing file pair: {ja_path} <-> {en_path}")
            rows.append(f"| `{ja_rel}` | `{en_rel}` | missing-file |")
            continue

        ja_blocks = extract_blocks(ja_path)
        en_blocks = extract_blocks(en_path)

        if ja_blocks == en_blocks:
            rows.append(f"| `{ja_rel}` | `{en_rel}` | aligned ({len(ja_blocks)} blocks) |")
            continue

        missing_in_en = [block for block in ja_blocks if block not in en_blocks]
        missing_in_ja = [block for block in en_blocks if block not in ja_blocks]
        order_differs = not missing_in_en and not missing_in_ja and ja_blocks != en_blocks

        details = []
        if missing_in_en:
            details.append(f"missing in en: {', '.join(missing_in_en)}")
        if missing_in_ja:
            details.append(f"missing in ja: {', '.join(missing_in_ja)}")
        if order_differs:
            details.append("block order differs")

        failures.append(f"{ja_rel} <-> {en_rel}: {'; '.join(details)}")
        rows.append(f"| `{ja_rel}` | `{en_rel}` | {'; '.join(details)} |")

    status = "passed" if not failures else "failed"
    report_lines = [
        "# Mirror Check Report",
        "",
        f"- status: {status}",
        f"- manuscript root: `{manuscript_root}`",
        "",
        "| JA | EN | Result |",
        "| --- | --- | --- |",
        *rows,
    ]

    if failures:
        report_lines.extend(["", "## Failures", ""])
        report_lines.extend([f"- {failure}" for failure in failures])

    return "\n".join(report_lines) + "\n", not failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate mirrored JA/EN manuscript block IDs.")
    parser.add_argument("--root", type=Path, default=Path("manuscript"))
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    manuscript_root = resolve_manuscript_root(args.root.resolve())
    report, ok = build_report(manuscript_root)

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")

    print(report, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
