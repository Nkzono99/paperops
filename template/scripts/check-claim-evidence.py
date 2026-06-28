#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import display_path, internal_path


PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|置き換えてください)")


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve_view_path(root: Path) -> tuple[str, Path] | None:
    candidates = [
        "notes/views/claim-evidence-map.md",
        "notes/claim-evidence-map.md",
    ]
    for rel_path in candidates:
        path = internal_path(root, rel_path)
        if path.exists():
            return display_path(root, path), path
    return None


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip() or PLACEHOLDER_RE.search(value) is not None


def normalize_header(value: str) -> str:
    aliases = {
        "主張id": "claim_id",
        "主張": "claim",
        "証拠": "evidence",
        "論拠・推論": "warrant_/_reasoning",
        "適用範囲": "scope",
        "限界": "limitation",
        "本文ブロック": "manuscript_blocks",
        "図表": "figure/table",
        "状態": "status",
    }
    normalized = value.strip().lower().replace(" ", "_")
    return aliases.get(value.strip().lower(), normalized)


def extract_claim_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(cell.replace(" ", "")) <= {"-", ":"} for cell in cells):
            continue
        if "Claim ID" in cells or "主張ID" in cells:
            headers = [normalize_header(cell) for cell in cells]
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def extract_not_claiming_items(text: str) -> list[str]:
    items: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() in {"## Not claiming", "## 主張しないこと"}
            continue
        if in_section and line.strip().startswith("- "):
            item = line.strip()[2:].strip()
            if not is_blank(item) and "本論文では" not in item and "将来課題" not in item:
                items.append(item)
    return items


def read_public_edge_text(root: Path) -> str:
    candidates = [
        "manuscript/ja/sections/00_abstract.tex",
        "manuscript/ja/sections/90_conclusion.tex",
        "manuscript/en/sections/00_abstract.tex",
        "manuscript/en/sections/90_conclusion.tex",
    ]
    chunks = []
    for rel_path in candidates:
        path = root / rel_path
        if path.exists():
            chunks.append(read_text(path))
    return "\n".join(chunks)


def warning_severity(strict: bool) -> str:
    return "error" if strict else "warning"


def check_claims(root: Path, text: str, rel_path: str, *, strict: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    rows = extract_claim_rows(text)
    if not rows:
        return [Finding(warning_severity(strict), f"`{rel_path}` に主張台帳が見つかりません")]

    for row in rows:
        claim_id = row.get("claim_id", "unknown")
        status = row.get("status", "").strip().lower()
        if status == "supported":
            for key in ["claim", "evidence", "warrant_/_reasoning", "scope", "manuscript_blocks"]:
                if is_blank(row.get(key)):
                    findings.append(Finding("error", f"`{claim_id}` は supported ですが `{key}` が未記入です"))
        if status == "overclaim risk" and is_blank(row.get("limitation")):
            findings.append(
                Finding(
                    warning_severity(strict),
                    f"`{claim_id}` は overclaim risk ですが limitation が未記入です",
                )
            )

    public_edge_text = read_public_edge_text(root)
    for item in extract_not_claiming_items(text):
        if item in public_edge_text:
            findings.append(
                Finding(
                    warning_severity(strict),
                    f"`主張しないこと` の `{item}` が Abstract/Conclusion に出現しています",
                )
            )

    if all(row.get("status", "").strip().lower() == "draft" for row in rows):
        findings.append(
            Finding(
                warning_severity(strict),
                "主張台帳は draft のみです。投稿前には supported / overclaim risk / defer を整理してください",
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="claim-evidence map の supported claim に証拠と本文対応があるか確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="投稿前 gate として警告級の claim drift も error にする。")
    args = parser.parse_args()

    root = args.root.resolve()
    resolved = resolve_view_path(root)
    if resolved is None:
        print("claim-evidence-check に失敗しました")
        print("- `_paperops/notes/views/claim-evidence-map.md` が見つかりません（旧互換: `notes/views/claim-evidence-map.md`, `notes/claim-evidence-map.md`）")
        return 1
    rel_path, path = resolved

    findings = check_claims(root, read_text(path), rel_path, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# claim-evidence-check")
    print("")
    if errors:
        print("## Errors")
        for finding in errors:
            print(f"- {finding.message}")
        print("")
    if warnings:
        print("## Warnings")
        for finding in warnings:
            print(f"- {finding.message}")
        print("")
    if not findings:
        print("supported claim に evidence、scope、本文 block の対応があります。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
