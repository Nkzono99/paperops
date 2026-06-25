#!/usr/bin/env python3
"""Validate the fixed paperops manuscript workflow state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_OVERALL_STATES = {
    "SCOPED",
    "EVIDENCE_READY",
    "STORY_LOCKED",
    "SECTION_PLANNED",
    "DRAFTED",
    "UNDER_REVIEW",
    "STRUCTURE_ACCEPTED",
    "POLISHED",
    "SUBMISSION_READY",
}
REQUIRED_ISSUE_CLASSES = {
    "evidence_loop",
    "story_loop",
    "section_loop",
    "prose_loop",
    "submission_loop",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="workflow/ の状態機械と現在状態を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[str] = []
    machine = load_mapping(root / "workflow" / "machine.yml", findings)
    current = load_mapping(root / "workflow" / "current-state.yml", findings)
    load_mapping(root / "workflow" / "decisions.yml", findings)
    load_mapping(root / "workflow" / "round-summary.yml", findings)

    if machine and current:
        validate_machine(machine, findings)
        validate_current(machine, current, findings)

    print("# workflow-check")
    print("")
    if findings:
        print("## Errors")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("workflow state is valid.")
    return 0


def validate_machine(machine: dict[str, Any], findings: list[str]) -> None:
    states = set(str(item) for item in machine.get("overall_states", []))
    missing_states = REQUIRED_OVERALL_STATES - states
    if missing_states:
        findings.append(f"machine.yml overall_states is missing: {', '.join(sorted(missing_states))}")

    issue_classes = machine.get("issue_classes", {})
    if not isinstance(issue_classes, dict):
        findings.append("machine.yml issue_classes must be a mapping")
        issue_classes = {}
    missing_classes = REQUIRED_ISSUE_CLASSES - set(str(key) for key in issue_classes)
    if missing_classes:
        findings.append(f"machine.yml issue_classes is missing: {', '.join(sorted(missing_classes))}")
    for name, spec in issue_classes.items():
        route_to = spec.get("route_to") if isinstance(spec, dict) else None
        if route_to not in states:
            findings.append(f"issue class `{name}` route_to `{route_to}` is not an overall state")

    transitions = machine.get("transitions", {})
    if not isinstance(transitions, dict):
        findings.append("machine.yml transitions must be a mapping")
        return
    for source, targets in transitions.items():
        if source not in states:
            findings.append(f"transition source `{source}` is not an overall state")
        if not isinstance(targets, list):
            findings.append(f"transition `{source}` targets must be a list")
            continue
        for target in targets:
            if target not in states:
                findings.append(f"transition `{source}` target `{target}` is not an overall state")


def validate_current(
    machine: dict[str, Any],
    current: dict[str, Any],
    findings: list[str],
) -> None:
    states = set(str(item) for item in machine.get("overall_states", []))
    section_states = set(str(item) for item in machine.get("section_states", []))
    issue_classes = set(str(key) for key in machine.get("issue_classes", {}))

    state = current.get("overall", {}).get("state") if isinstance(current.get("overall"), dict) else None
    if state not in states:
        findings.append(f"current-state.yml overall.state `{state}` is not an overall state")

    guards = machine.get("guards", {})
    current_guards = current.get("guards", {})
    if isinstance(guards, dict):
        for target, required in guards.items():
            values = current_guards.get(target, {}) if isinstance(current_guards, dict) else {}
            if not isinstance(required, list) or not isinstance(values, dict):
                findings.append(f"guard `{target}` must have list requirements and mapping values")
                continue
            for key in required:
                if key not in values:
                    findings.append(f"current-state.yml guards.{target}.{key} is missing")

    sections = current.get("sections", {})
    if not isinstance(sections, dict):
        findings.append("current-state.yml sections must be a mapping")
        return
    for name, section in sections.items():
        if not isinstance(section, dict):
            findings.append(f"section `{name}` must be a mapping")
            continue
        section_state = section.get("state")
        if section_state not in section_states:
            findings.append(f"section `{name}` state `{section_state}` is not valid")
        if section_state == "STALE" and section.get("route") not in issue_classes:
            findings.append(f"stale section `{name}` must have a valid route")
        depends_on = section.get("depends_on", {})
        if not isinstance(depends_on, dict):
            findings.append(f"section `{name}` depends_on must be a mapping")
            continue
        for kind, refs in depends_on.items():
            if not isinstance(refs, list):
                findings.append(f"section `{name}` depends_on.{kind} must be a list")
                continue
            for ref in refs:
                if "@" not in str(ref):
                    findings.append(f"section `{name}` dependency `{ref}` should include @version")


def load_mapping(path: Path, findings: list[str]) -> dict[str, Any]:
    if not path.exists():
        findings.append(f"`{path.relative_to(path.parents[1])}` is missing")
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            findings.append(f"`{path}` is not valid workflow YAML/JSON: {exc}")
            return {}
    if not isinstance(data, dict):
        findings.append(f"`{path}` must contain a mapping")
        return {}
    return data


if __name__ == "__main__":
    raise SystemExit(main())
