#!/usr/bin/env python3
"""Detect manuscript-finishing work that drifts away from content blockers."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_paths import internal_path
from paperops_typed_views import workflow_projection


CONTENT_GUARD_STATES = [
    "STORY_SEEDED",
    "EVIDENCE_PLANNED",
    "EVIDENCE_READY",
    "STORY_RECONCILED",
    "ARCHITECTURE_LOCKED",
    "SECTION_PLANNED",
    "STRUCTURE_ACCEPTED",
]
CONTENT_FIRST_GUARD = "CONTENT_FIRST"
SUBMISSION_INTENTS = {"submission"}
HARNESS_INTENTS = {"harness"}

HYGIENE_PATHS = (
    "submission/",
    "manuscript/publication-metadata.toml",
    "manuscript/venue.md",
    "_paperops/notes/ai-use.md",
    "notes/ai-use.md",
)
HARNESS_PATHS = (
    "scripts/",
    "Makefile",
    ".agents/skills/",
    ".claude/skills/",
    "_paperops/defaults/workflow/machine.yml",
    "_paperops/defaults/workflow/focus-policy.yml",
    "_paperops/workflow/machine.yml",
    "_paperops/workflow/focus-policy.yml",
    "workflow/machine.yml",
    "workflow/focus-policy.yml",
)
CONTENT_PATHS = (
    "manuscript/ja/",
    "manuscript/en/",
    "story/",
    "_paperops/model/research/",
    "_paperops/model/editorial/",
    "_paperops/model/manuscript/",
    "_paperops/model/issues/",
    "_paperops/figures/",
    "_paperops/notes/views/storyline.md",
    "_paperops/notes/views/claim-evidence-map.md",
    "_paperops/notes/views/result-pattern-map.md",
    "_paperops/notes/reviewer-model.md",
    "claims/",
    "evidence/",
    "figures/",
    "notes/views/storyline.md",
    "notes/views/claim-evidence-map.md",
    "notes/views/result-pattern-map.md",
    "notes/reviewer-model.md",
    "review/",
    "requests/",
    "workflow/current-state.yml",
    "workflow/round-summary.yml",
)
SUBAGENT_REPORT_PATHS = (
    "_paperops/model/issues/rounds/subagent-report-",
    "_paperops/model/issues/rounds/subagent-reports/",
    "review/rounds/subagent-report-",
    "review/rounds/subagent-reports/",
)


@dataclass
class Finding:
    severity: str
    message: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="finish-manuscript が本文 blocker より submission/harness 作業へ逸れていないか確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--phase", choices=["start", "progress", "finish"], default="progress")
    parser.add_argument(
        "--intent",
        choices=["content", "evidence", "prose", "submission", "harness"],
        default="content",
    )
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--since", default="HEAD")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(
        root=root,
        phase=args.phase,
        intent=args.intent,
        changed_files=list(args.changed_file) or changed_files_from_git(root, args.since),
        strict=args.strict,
    )
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# content-first-check")
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
        print("content intent is aligned with the current manuscript content blocker.")
    return 1 if errors else 0


def check(root: Path, phase: str, intent: str, changed_files: list[str], strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    projection = workflow_projection(root)
    sections = projection["sections"]
    missing_sections = [name for name in ("results", "discussion") if sections.get(name) != "verified"]
    content_blocker_open = bool(missing_sections or projection["open_issue_ids"])
    changed_kinds = classify_changed_files(changed_files)

    if phase == "finish":
        if content_blocker_open:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "finish-manuscript cannot complete before typed Results/Discussion sections are verified and blocking issues close: "
                    + ", ".join(missing_sections + list(projection["open_issue_ids"]))
                    + ".",
                )
            )

    if content_blocker_open and intent in SUBMISSION_INTENTS:
        findings.append(
            Finding(
                "error" if strict else "warning",
                "Submission hygiene is blocked until typed Results/Discussion sections are verified; resolve manuscript content blocker first.",
            )
        )

    if content_blocker_open and intent in HARNESS_INTENTS:
        findings.append(
            Finding(
                "error" if strict else "warning",
                "downstream harness work is blocked during a manuscript goal; summarize it for feedback-paper-harness and return to manuscript content.",
            )
        )

    if phase == "progress" and content_blocker_open and changed_files:
        if changed_kinds <= {"subagent_report"}:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "subagent reports are not manuscript edits; convert the report into typed Issue/Research updates or Manuscript section plans before treating it as progress on a manuscript content blocker.",
                )
            )
        if changed_kinds <= {"hygiene"}:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "Only Submission hygiene files changed while manuscript content blocker remains open.",
                )
            )
        if changed_kinds <= {"harness"}:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "Only downstream harness files changed while manuscript content blocker remains open; route the gap to feedback-paper-harness.",
                )
            )
        if changed_kinds <= {"hygiene", "harness"} and "content" not in changed_kinds:
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "No content artifact changed while Results/Discussion/storyline guards are still unresolved.",
                )
            )

    if not findings and content_blocker_open:
        # Positive output keeps the check useful as a self-critique prompt.
        return []
    return findings


def missing_content_guards(current: dict[str, Any]) -> dict[str, list[str]]:
    guards = current.get("guards", {})
    if not isinstance(guards, dict):
        return {state: ["guards mapping missing"] for state in CONTENT_GUARD_STATES}
    missing: dict[str, list[str]] = {}
    for state in CONTENT_GUARD_STATES:
        missing[state] = missing_guard_values(current, state)
    return missing


def missing_guard_values(current: dict[str, Any], state: str) -> list[str]:
    guards = current.get("guards", {})
    if not isinstance(guards, dict):
        return ["guards mapping missing"]
    values = guards.get(state, {})
    if not isinstance(values, dict):
        return ["guard values missing"]
    return [str(key) for key, value in values.items() if value is not True]


def classify_changed_files(paths: list[str]) -> set[str]:
    kinds: set[str] = set()
    for raw_path in paths:
        path = raw_path.strip().lstrip("./")
        if not path:
            continue
        if matches_any(path, SUBAGENT_REPORT_PATHS):
            kinds.add("subagent_report")
        elif matches_any(path, HYGIENE_PATHS):
            kinds.add("hygiene")
        elif matches_any(path, HARNESS_PATHS):
            kinds.add("harness")
        elif matches_any(path, CONTENT_PATHS):
            kinds.add("content")
        else:
            kinds.add("other")
    return kinds


def matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(path == pattern.rstrip("/") or path.startswith(pattern) for pattern in patterns)


def changed_files_from_git(root: Path, since: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", since],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def load_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
