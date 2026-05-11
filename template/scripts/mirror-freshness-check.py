#!/usr/bin/env python3

import argparse
import hashlib
from datetime import date
from pathlib import Path
import re


BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(?P<block_id>[A-Za-z0-9_.-]+)\s*$")
PAIR_HEADER_RE = re.compile(r"^\s*\[\[file_pair\]\]\s*$")
ASSIGN_RE = re.compile(r'^\s*(?P<key>ja|en)\s*=\s*"(?P<value>[^"]+)"\s*$')


def resolve_manuscript_root(root: Path) -> Path:
    if (root / "mirror" / "map.toml").exists():
        return root
    if (root / "manuscript" / "mirror" / "map.toml").exists():
        return root / "manuscript"
    raise FileNotFoundError(f"{root} 配下に manuscript/mirror/map.toml が見つかりません")


def load_file_pairs(map_path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    current: dict[str, str] = {}
    for line in map_path.read_text(encoding="utf-8").splitlines():
        if PAIR_HEADER_RE.match(line):
            if "ja" in current and "en" in current:
                pairs.append((current["ja"], current["en"]))
            current = {}
            continue
        match = ASSIGN_RE.match(line)
        if match:
            current[match.group("key")] = match.group("value")
    if "ja" in current and "en" in current:
        pairs.append((current["ja"], current["en"]))
    return pairs


def extract_block_text(path: Path) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current_id: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = BLOCK_RE.match(line)
        if match:
            current_id = match.group("block_id")
            blocks.setdefault(current_id, [])
            continue
        if current_id is not None:
            blocks[current_id].append(line.rstrip())
    return {block_id: "\n".join(lines).strip() for block_id, lines in blocks.items()}


def digest(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def build_entries(manuscript_root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for ja_rel, en_rel in load_file_pairs(manuscript_root / "mirror" / "map.toml"):
        ja_blocks = extract_block_text(manuscript_root / ja_rel)
        en_blocks = extract_block_text(manuscript_root / en_rel)
        for block_id in sorted(set(ja_blocks) | set(en_blocks)):
            entries.append(
                {
                    "id": block_id,
                    "source_file": ja_rel,
                    "target_file": en_rel,
                    "source_hash_at_last_sync": digest(ja_blocks.get(block_id, "")),
                    "target_hash_at_last_sync": digest(en_blocks.get(block_id, "")),
                    "status": "synced",
                    "last_sync": date.today().isoformat(),
                }
            )
    return entries


def quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_ledger(path: Path, entries: list[dict[str, str]]) -> None:
    lines = [
        "# Block freshness ledger",
        "# Regenerate after reviewed ja/en synchronization:",
        "# python scripts/mirror-freshness-check.py --root manuscript --update",
        "version: 1",
        "blocks:",
    ]
    for entry in entries:
        lines.append(f"  - id: {quote(entry['id'])}")
        lines.append(f"    source_file: {quote(entry['source_file'])}")
        lines.append(f"    target_file: {quote(entry['target_file'])}")
        lines.append(f"    source_hash_at_last_sync: {quote(entry['source_hash_at_last_sync'])}")
        lines.append(f"    target_hash_at_last_sync: {quote(entry['target_hash_at_last_sync'])}")
        lines.append(f"    status: {quote(entry['status'])}")
        lines.append(f"    last_sync: {quote(entry['last_sync'])}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clean_scalar(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_ledger(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            current = {}
            entries.append(current)
            remainder = stripped[2:].strip()
            if ":" in remainder:
                key, value = remainder.split(":", 1)
                current[key.strip()] = clean_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = clean_scalar(value)
    return entries


def key(entry: dict[str, str]) -> tuple[str, str, str]:
    return (entry.get("source_file", ""), entry.get("target_file", ""), entry.get("id", ""))


def check_freshness(manuscript_root: Path, ledger_path: Path) -> tuple[list[str], list[str]]:
    current_entries = {key(entry): entry for entry in build_entries(manuscript_root)}
    ledger_entries = {key(entry): entry for entry in load_ledger(ledger_path)}
    errors: list[str] = []
    warnings: list[str] = []

    for entry_key, current in sorted(current_entries.items()):
        recorded = ledger_entries.get(entry_key)
        label = f"`{current['id']}` ({current['source_file']} -> {current['target_file']})"
        if recorded is None:
            warnings.append(f"{label} が `block-ledger.yml` にありません")
            continue
        changed = []
        if current["source_hash_at_last_sync"] != recorded.get("source_hash_at_last_sync"):
            changed.append("source")
        if current["target_hash_at_last_sync"] != recorded.get("target_hash_at_last_sync"):
            changed.append("target")
        if changed:
            status = recorded.get("status", "synced")
            warnings.append(f"{label} は前回 ledger から {', '.join(changed)} が変わっています（status: {status}）")

    for entry_key, recorded in sorted(ledger_entries.items()):
        if entry_key not in current_entries:
            warnings.append(f"`{recorded.get('id', 'unknown')}` は ledger にありますが現在の map/block にありません")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="日英 block の前回同期ハッシュから freshness drift を確認する。")
    parser.add_argument("--root", type=Path, default=Path("manuscript"))
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--update", action="store_true", help="現在の block hash で ledger を更新する。")
    args = parser.parse_args()

    manuscript_root = resolve_manuscript_root(args.root.resolve())
    ledger_path = args.ledger or manuscript_root / "mirror" / "block-ledger.yml"

    if args.update:
        write_ledger(ledger_path, build_entries(manuscript_root))
        print(f"`{ledger_path}` を更新しました")
        return 0

    print("# mirror-freshness-check")
    print("")
    if not ledger_path.exists():
        print("## Warnings")
        print(f"- `{ledger_path}` がありません。`--update` で初期化してください。")
        return 0

    errors, warnings = check_freshness(manuscript_root, ledger_path)
    if errors:
        print("## Errors")
        for item in errors:
            print(f"- {item}")
        print("")
    if warnings:
        print("## Warnings")
        for item in warnings:
            print(f"- {item}")
        print("")
    if not errors and not warnings:
        print("block freshness ledger と現在の ja/en block は一致しています。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
