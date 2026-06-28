#!/usr/bin/env python3
"""Audit predicted-result authoring scaffolds before submission."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from paperops_paths import internal_path


MARKERS = ("PREDICTED-RESULT", "SIM-REQUEST", "EXPECTATION-BASIS", "REPLACE-XX")
MARKER_RE = re.compile(r"(?<!\\)%\s*(PREDICTED-RESULT|SIM-REQUEST|EXPECTATION-BASIS|REPLACE-XX)\s*:?\s*(.*)$")
BLOCK_RE = re.compile(r"^\s*%\s*block:\s*(\S+)")
REQUEST_RE = re.compile(r"\bAREQ-[A-Za-z0-9_.-]+\b")
XX_RE = re.compile(
    r"(?i)(?:\b(?:approximately|approx\.?|around|about)\s+xx\b|(?:Fig\.|Figure)\s*xx\b|約\s*xx\b|(?<![A-Za-z0-9])xx(?![A-Za-z0-9]))"
)
INACTIVE_STATUSES = {
    "closed",
    "resolved",
    "done",
    "complete",
    "completed",
    "cancelled",
    "canceled",
    "rejected",
    "abandoned",
    "reconciled",
}


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class MarkerHit:
    marker: str
    body: str
    rel_path: str
    line_number: int
    block_id: str


@dataclass
class BlockState:
    block_id: str
    rel_path: str
    markers: dict[str, list[MarkerHit]] = field(default_factory=dict)

    @property
    def marker_names(self) -> set[str]:
        return set(self.markers)

    @property
    def request_ids(self) -> set[str]:
        ids: set[str] = set()
        for hits in self.markers.values():
            for hit in hits:
                ids.update(REQUEST_RE.findall(hit.body))
        return ids


@dataclass
class PlaceholderHit:
    rel_path: str
    line_number: int
    block_id: str
    excerpt: str


def split_tex_comment(line: str) -> tuple[str, str]:
    chars: list[str] = []
    escaped = False
    for index, char in enumerate(line):
        if char == "%" and not escaped:
            return "".join(chars), line[index + 1 :]
        chars.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return "".join(chars), ""


def clean_excerpt(text: str, limit: int = 120) -> str:
    excerpt = re.sub(r"\s+", " ", text).strip()
    if len(excerpt) > limit:
        excerpt = excerpt[: limit - 3].rstrip() + "..."
    return f"`{excerpt}`"


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        fields[key.strip()] = raw_value.strip().strip('"').strip("'")
    return fields


def request_cards(root: Path) -> dict[str, str]:
    base = internal_path(root, "requests", "analysis")
    if not base.exists():
        return {}
    requests: dict[str, str] = {}
    for path in sorted(base.glob("*.md")):
        if path.name == "analysis-request-template.md":
            continue
        fields = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        request_id = fields.get("id", "").strip() or path.stem
        status = fields.get("status", "").strip() or "open"
        if request_id:
            requests[request_id] = status
    return requests


def candidate_files(root: Path, scope: str) -> list[tuple[Path, str]]:
    groups: list[tuple[Path, str]] = []
    if scope in {"authoring", "all"}:
        manuscript = root / "manuscript"
        if manuscript.exists():
            groups.extend((path, "authoring") for path in sorted(manuscript.glob("**/*.tex")) if path.is_file())
    if scope in {"submission", "all"}:
        submission = root / "submission"
        if submission.exists():
            groups.extend((path, "submission") for path in sorted(submission.glob("**/*.tex")) if path.is_file())
    return groups


def collect_blocks_and_placeholders(root: Path, scope: str) -> tuple[dict[tuple[str, str], BlockState], list[PlaceholderHit], bool]:
    blocks: dict[tuple[str, str], BlockState] = {}
    placeholders: list[PlaceholderHit] = []
    saw_submission_scope = False

    for path, group in candidate_files(root, scope):
        saw_submission_scope = saw_submission_scope or group == "submission"
        rel_path = path.relative_to(root).as_posix()
        current_block = "unknown"
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            block_match = BLOCK_RE.match(line)
            if block_match:
                current_block = block_match.group(1)
            marker_match = MARKER_RE.search(line)
            if marker_match:
                key = (rel_path, current_block)
                block = blocks.setdefault(key, BlockState(block_id=current_block, rel_path=rel_path))
                marker = marker_match.group(1)
                block.markers.setdefault(marker, []).append(
                    MarkerHit(
                        marker=marker,
                        body=marker_match.group(2).strip(),
                        rel_path=rel_path,
                        line_number=line_number,
                        block_id=current_block,
                    )
                )
            prose, _comment = split_tex_comment(line)
            if XX_RE.search(prose):
                placeholders.append(
                    PlaceholderHit(
                        rel_path=rel_path,
                        line_number=line_number,
                        block_id=current_block,
                        excerpt=clean_excerpt(prose),
                    )
                )
    return blocks, placeholders, saw_submission_scope


def severity_for(strict: bool, scope: str, rel_path: str) -> str:
    if strict or scope == "submission" or rel_path.startswith("submission/"):
        return "error"
    return "warning"


def check(root: Path, scope: str, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    blocks, placeholders, saw_submission_scope = collect_blocks_and_placeholders(root, scope)
    requests = request_cards(root)

    for block in blocks.values():
        severity = severity_for(strict, scope, block.rel_path)
        findings.append(
            Finding(
                severity,
                f"`{block.rel_path}` block `{block.block_id}` contains predicted-result authoring source markers "
                f"({', '.join(sorted(block.marker_names))}; requests={', '.join(sorted(block.request_ids)) or 'none'}). "
                "It cannot become a submission candidate until materialized.",
            )
        )
        missing = [marker for marker in MARKERS if marker not in block.marker_names]
        if missing:
            findings.append(
                Finding(
                    severity,
                    f"`{block.rel_path}` block `{block.block_id}` is missing predicted-result marker(s): {', '.join(missing)}",
                )
            )
        request_ids = block.request_ids
        if not request_ids:
            findings.append(
                Finding(
                    severity,
                    f"`{block.rel_path}` block `{block.block_id}` has no `AREQ-*` analysis request reference.",
                )
            )
        for request_id in sorted(request_ids):
            if request_id not in requests:
                findings.append(
                    Finding(
                        severity,
                        f"`{block.rel_path}` block `{block.block_id}` references `{request_id}`, but no analysis request card exists.",
                    )
                )

    for placeholder in placeholders:
        severity = severity_for(strict, scope, placeholder.rel_path)
        findings.append(
            Finding(
                severity,
                f"`{placeholder.rel_path}:{placeholder.line_number}` block `{placeholder.block_id}` contains an xx placeholder in prose: {placeholder.excerpt}",
            )
        )

    if strict or saw_submission_scope:
        active_prediction_statuses = {"planned", "predicted", "analysis-needed", "open", "running"}
        for request_id, status in sorted(requests.items()):
            normalized = status.strip().lower()
            if normalized in active_prediction_statuses and normalized not in INACTIVE_STATUSES:
                findings.append(
                    Finding(
                        "error",
                        f"`{request_id}` is an unresolved analysis request (`status={status}`); close, abandon, or reconcile it before submission.",
                    )
                )

    return findings


def render(findings: list[Finding]) -> None:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# predicted-results-check")
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
    if findings:
        print(
            "`manuscript/` is an authoring source and may carry managed predictions, "
            "but a submission candidate must not contain predicted markers, xx placeholders, "
            "or unresolved analysis requests."
        )
    else:
        print("予測稿 marker、xx placeholder、未解決予測 request は見つかりませんでした。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="未検証の予測稿 marker、xx placeholder、submission candidate に残る analysis request を確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--scope", choices=["authoring", "submission", "all"], default="authoring")
    parser.add_argument("--strict", action="store_true", help="authoring source の warning も error として扱う。")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(root, args.scope, args.strict)
    render(findings)
    return 1 if any(finding.severity == "error" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
