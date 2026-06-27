#!/usr/bin/env python3
"""Check whether manuscript references are represented by paperops cards."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import display_path, internal_path


FIGURE_RE = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}")
CITATION_RE = re.compile(r"\\[A-Za-z]*cite[A-Za-z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]+)\}")
BLOCK_RE = re.compile(r"%\s*block:\s*([A-Za-z0-9_.:-]+)")


@dataclass(frozen=True)
class ManuscriptUse:
    kind: str
    value: str
    path: Path


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def manuscript_files(root: Path) -> list[Path]:
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return []
    return sorted(
        path
        for path in manuscript.rglob("*.tex")
        if "/build/" not in path.as_posix() and "/mirror/" not in path.as_posix()
    )


def normalize_figure_path(raw: str) -> str:
    text = raw.strip().replace("\\", "/")
    text = re.sub(r"^\./", "", text)
    if text.startswith("manuscript/shared/figures/"):
        return text
    if "shared/figures/" in text:
        suffix = text.split("shared/figures/", 1)[1]
        return f"manuscript/shared/figures/{suffix}"
    if text.startswith("figures/"):
        return f"manuscript/shared/{text}"
    return text


def collect_manuscript_uses(root: Path) -> list[ManuscriptUse]:
    uses: list[ManuscriptUse] = []
    for path in manuscript_files(root):
        text = read_text(path)
        for match in FIGURE_RE.finditer(text):
            uses.append(ManuscriptUse("figure", normalize_figure_path(match.group(1)), path))
        for match in CITATION_RE.finditer(text):
            for key in match.group(1).split(","):
                key = key.strip()
                if key:
                    uses.append(ManuscriptUse("citation", key, path))
        for match in BLOCK_RE.finditer(text):
            block_id = match.group(1)
            if any(char.isalnum() for char in block_id):
                uses.append(ManuscriptUse("block", block_id, path))
    return uses


def card_files(root: Path, *parts: str) -> list[Path]:
    base = internal_path(root, *parts)
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob("*.md")
        if not path.name.endswith("-template.md") and "README" not in path.name
    )


def card_texts(paths: list[Path]) -> list[str]:
    return [read_text(path) for path in paths]


def registered_figure(use: ManuscriptUse, texts: list[str]) -> bool:
    basename = Path(use.value).name
    for text in texts:
        normalized_text = text.replace("\\", "/")
        if use.value in normalized_text or basename in normalized_text:
            return True
    return False


def registered_literal(value: str, texts: list[str]) -> bool:
    return any(value in text for text in texts)


def ledger_block_ids(root: Path) -> set[str]:
    ledger = root / "manuscript" / "mirror" / "block-ledger.yml"
    if not ledger.exists():
        return set()
    text = read_text(ledger)
    return set(re.findall(r"\bid:\s*[\"']?([A-Za-z0-9_.:-]+)[\"']?", text))


def check(root: Path, strict: bool) -> list[Finding]:
    uses = collect_manuscript_uses(root)
    figure_texts = card_texts(card_files(root, "evidence", "figures"))
    source_texts = card_texts(card_files(root, "evidence", "sources"))
    block_texts = card_texts(
        card_files(root, "evidence")
        + card_files(root, "claims")
        + card_files(root, "review")
        + card_files(root, "requests")
    )
    registered_blocks = ledger_block_ids(root)
    severity = "error" if strict else "warning"
    findings: list[Finding] = []

    for use in uses:
        if use.kind == "figure" and not registered_figure(use, figure_texts):
            findings.append(
                Finding(
                    severity,
                    f"unregistered figure asset `{use.value}` used in `{display_path(root, use.path)}`",
                )
            )
        elif use.kind == "citation" and not registered_literal(use.value, source_texts):
            findings.append(
                Finding(
                    severity,
                    f"unregistered citation key `{use.value}` used in `{display_path(root, use.path)}`",
                )
            )
        elif (
            use.kind == "block"
            and use.value not in registered_blocks
            and not registered_literal(use.value, block_texts)
        ):
            findings.append(
                Finding(
                    severity,
                    f"unregistered manuscript block `{use.value}` used in `{display_path(root, use.path)}`",
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="原稿内の図・引用・block ID が paperops card に接続されているか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(root, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# card-coverage-check")
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
        print("coverage gaps are not detected.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
