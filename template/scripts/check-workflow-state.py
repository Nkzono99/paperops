#!/usr/bin/env python3
"""Validate the fixed paperops manuscript workflow state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from paperops_paths import display_path, internal_path
from paperops_typed_views import TypedViewError, workflow_projection


REQUIRED_OVERALL_STATES = {
    "SCOPED",
    "STORY_SEEDED",
    "EVIDENCE_PLANNED",
    "EVIDENCE_READY",
    "STORY_RECONCILED",
    "ARCHITECTURE_LOCKED",
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
REQUIRED_SUBAGENT_ROLES = {
    "story_architect",
    "evidence_auditor",
    "results_structure_reviewer",
    "discussion_function_reviewer",
    "figure_story_reviewer",
    "public_reader",
    "reviewer_panel",
    "submission_hygienist",
}
REQUIRED_SUBAGENT_ROLE_FIELDS = {
    "purpose",
    "entry_condition",
    "allowed_inputs",
    "outputs",
    "route_bias",
}
STRUCTURE_ACCEPTED_OR_LATER = {"STRUCTURE_ACCEPTED", "POLISHED", "SUBMISSION_READY"}
BLOCK_FLOW_REQUIRED_SECTIONS = {"results", "discussion"}


def main() -> int:
    parser = argparse.ArgumentParser(description="workflow/ の状態機械と現在状態を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[str] = []
    machine = load_mapping(root, internal_path(root, "workflow", "machine.yml"), findings)
    subagent_roster = load_mapping(root, internal_path(root, "workflow", "subagent-roster.yml"), findings)

    if machine:
        validate_machine(machine, findings)
    try:
        projection = workflow_projection(root)
        if projection["submission"] not in {"authoring", "candidate", "gated", "revision_candidate", "frozen", "submitted", "under_review", "resubmitted", "accepted", "rejected", "withdrawn"}:
            findings.append("typed Publication Model has an unknown submission state")
    except TypedViewError as error:
        findings.append(str(error))
    if subagent_roster:
        validate_subagent_roster(subagent_roster, findings)

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


def validate_state_consistency(current: dict[str, Any], findings: list[str]) -> None:
    overall = current.get("overall", {})
    overall_state = overall.get("state") if isinstance(overall, dict) else None
    sections = current.get("sections", {})
    if not isinstance(sections, dict):
        return

    accepted_like = {"AUDITED", "ACCEPTED"}
    if overall_state in STRUCTURE_ACCEPTED_OR_LATER:
        for name in sorted(BLOCK_FLOW_REQUIRED_SECTIONS):
            section = sections.get(name)
            section_state = section.get("state") if isinstance(section, dict) else None
            if section_state not in accepted_like:
                findings.append(
                    f"current-state.yml overall.state `{overall_state}` requires section `{name}` "
                    "to be AUDITED or ACCEPTED after block-flow review; "
                    f"section `{name}` is `{section_state}`"
                )

    if overall_state == "POLISHED":
        for name, section in sections.items():
            if not isinstance(section, dict):
                continue
            section_state = section.get("state")
            if section_state not in accepted_like:
                findings.append(
                    "current-state.yml overall.state `POLISHED` requires every manuscript section "
                    f"to be AUDITED or ACCEPTED; section `{name}` is `{section_state}`"
                )


def validate_subagent_roster(roster: dict[str, Any], findings: list[str]) -> None:
    if roster.get("schema_version") != 1:
        findings.append("subagent-roster.yml schema_version must be 1")
    if roster.get("mode") != "orchestrated_manuscript_writing":
        findings.append("subagent-roster.yml mode must be orchestrated_manuscript_writing")

    for field in ["orchestrator", "delegation_contract", "integration_contract", "roles"]:
        if field not in roster:
            findings.append(f"subagent-roster.yml {field} is missing")

    roles = roster.get("roles", [])
    if not isinstance(roles, list):
        findings.append("subagent-roster.yml roles must be a list")
        return

    role_by_id: dict[str, dict[str, Any]] = {}
    for index, role in enumerate(roles):
        if not isinstance(role, dict):
            findings.append(f"subagent-roster.yml role at index {index} must be a mapping")
            continue
        role_id = role.get("id")
        if not isinstance(role_id, str) or not role_id:
            findings.append(f"subagent-roster.yml role at index {index} id is missing")
            continue
        role_by_id[role_id] = role
        for field in REQUIRED_SUBAGENT_ROLE_FIELDS:
            if field not in role:
                findings.append(f"subagent-roster.yml role `{role_id}` {field} is missing")
        for list_field in ["allowed_inputs", "outputs"]:
            if list_field in role and not isinstance(role[list_field], list):
                findings.append(f"subagent-roster.yml role `{role_id}` {list_field} must be a list")

    missing_roles = REQUIRED_SUBAGENT_ROLES - set(role_by_id)
    if missing_roles:
        findings.append(
            "subagent-roster.yml roles is missing: " + ", ".join(sorted(missing_roles))
        )

    submission_role = role_by_id.get("submission_hygienist", {})
    entry_condition = submission_role.get("entry_condition")
    if isinstance(entry_condition, str) and "STRUCTURE_ACCEPTED" not in entry_condition:
        findings.append(
            "subagent-roster.yml role `submission_hygienist` entry_condition must include STRUCTURE_ACCEPTED"
        )

    public_reader = role_by_id.get("public_reader", {})
    public_inputs = public_reader.get("allowed_inputs", [])
    if isinstance(public_inputs, list):
        for item in public_inputs:
            text = str(item)
            if "public" not in text and "sanitized" not in text:
                findings.append(
                    "subagent-roster.yml role `public_reader` allowed_inputs must stay public-only"
                )
                break


def load_mapping(root: Path, path: Path, findings: list[str]) -> dict[str, Any]:
    if not path.exists():
        findings.append(f"`{display_path(root, path)}` is missing")
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            findings.append(f"`{display_path(root, path)}` is not valid workflow YAML/JSON: {exc}")
            return {}
    if not isinstance(data, dict):
        findings.append(f"`{display_path(root, path)}` must contain a mapping")
        return {}
    return data


if __name__ == "__main__":
    raise SystemExit(main())
