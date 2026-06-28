"""Shared helpers for template checker scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    collected: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(collected)
        collected.append(line)
    return ""


def warning_severity(strict: bool) -> str:
    return "error" if strict else "warning"


def partition_findings(findings: list[Finding]) -> tuple[list[Finding], list[Finding]]:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    return errors, warnings


def emit_findings(
    title: str,
    findings: list[Finding],
    *,
    success_message: str,
    fail_on_warnings: bool = False,
) -> int:
    errors, warnings = partition_findings(findings)

    print(f"# {title}")
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
        print(success_message)

    return 1 if errors or (fail_on_warnings and warnings) else 0
