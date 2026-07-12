#!/usr/bin/env python3
"""Check whether manuscript references are represented by paperops cards."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_checks import Finding, emit_findings, read_text
from paperops_paths import display_path
from paperops_typed_views import indexed_documents


FIGURE_RE = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}")
CITATION_RE = re.compile(r"\\[A-Za-z]*cite[A-Za-z*]*(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]+)\}")
BLOCK_RE = re.compile(r"%\s*block:\s*([A-Za-z0-9_.:-]+)")


@dataclass(frozen=True)
class ManuscriptUse:
    kind: str
    value: str
    path: Path


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


def typed_texts(root: Path, model: str, record_type: str | None = None) -> list[str]:
    return [repr(item.document) for item in indexed_documents(root, model, record_type)]


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
    figure_texts = typed_texts(root, "research", "figure")
    source_texts = typed_texts(root, "research", "source")
    block_documents = indexed_documents(root, "manuscript", "block")
    block_texts = [repr(item.document) for item in block_documents]
    registered_blocks = ledger_block_ids(root) | {
        value
        for item in block_documents
        for value in (item.object_id, item.document.get("ja_tex_block_id"), item.document.get("en_tex_block_id"))
        if isinstance(value, str) and value
    }
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
        description="原稿内の図・引用・block ID が typed model に接続されているか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    return emit_findings(
        "card-coverage-check",
        check(root, strict=args.strict),
        success_message="coverage gaps are not detected.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
