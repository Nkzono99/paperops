"""Fixed manuscript workflow state-machine helpers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from paperops.cli.project import find_project_root


MACHINE_REL = Path("workflow") / "machine.yml"
CURRENT_REL = Path("workflow") / "current-state.yml"
ROUND_REL = Path("workflow") / "round-summary.yml"


def add_workflow_parser(
    subcommands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    workflow_parser = subcommands.add_parser(
        "workflow",
        help="Inspect and update the manuscript workflow state.",
    )
    workflow_subcommands = workflow_parser.add_subparsers(
        dest="workflow_action",
        required=True,
    )

    status_parser = workflow_subcommands.add_parser("status", help="Show workflow state.")
    status_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    status_parser.set_defaults(func=cmd_workflow)

    next_parser = workflow_subcommands.add_parser("next", help="Show likely next transition.")
    next_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    next_parser.set_defaults(func=cmd_workflow)

    advance_parser = workflow_subcommands.add_parser(
        "advance",
        help="Advance the overall workflow state when guards pass.",
    )
    advance_parser.add_argument("target_state", help="Target overall state.")
    advance_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    advance_parser.set_defaults(func=cmd_workflow)

    invalidate_parser = workflow_subcommands.add_parser(
        "invalidate",
        help="Mark sections depending on an artifact as stale.",
    )
    invalidate_parser.add_argument("artifact_id", help="Artifact id such as CLM-0003.")
    invalidate_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    invalidate_parser.set_defaults(func=cmd_workflow)

    route_parser = workflow_subcommands.add_parser(
        "route-review",
        help="Route a review issue class to the right workflow depth.",
    )
    route_parser.add_argument("path", nargs="?", type=Path, help="Project directory.")
    route_parser.add_argument("--issue-class", default="", help="Issue class to route.")
    route_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the routed overall state and increment its loop counter.",
    )
    route_parser.set_defaults(func=cmd_workflow)
    return workflow_parser


def cmd_workflow(args: argparse.Namespace) -> int:
    root = find_project_root(args.path or Path.cwd())
    if root is None:
        print("error: this does not look like a paper harness project.", file=sys.stderr)
        return 2
    args.project_root = root

    try:
        machine = load_mapping(root / MACHINE_REL)
        current = load_mapping(root / CURRENT_REL)
    except WorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.workflow_action == "status":
        return workflow_status(current)
    if args.workflow_action == "next":
        return workflow_next(machine, current)
    if args.workflow_action == "advance":
        return workflow_advance(root, machine, current, args.target_state)
    if args.workflow_action == "invalidate":
        return workflow_invalidate(root, machine, current, args.artifact_id)
    if args.workflow_action == "route-review":
        return workflow_route_review(root, machine, current, args.issue_class, apply=args.apply)
    print(f"error: unknown workflow action: {args.workflow_action}", file=sys.stderr)
    return 2


def workflow_status(current: dict[str, Any]) -> int:
    state = overall_state(current)
    print(f"workflow state: {state}")
    stale = stale_sections(current)
    if stale:
        print("stale sections:")
        for name, section in stale:
            route = section.get("route", "section_loop")
            reason = section.get("stale_reason", "")
            suffix = f" ({reason})" if reason else ""
            print(f"- {name} -> {route}{suffix}")
    else:
        print("stale sections: none")
    blockers = current.get("review", {}).get("blocking_concerns", [])
    majors = current.get("review", {}).get("major_concerns", [])
    print(f"blocking concerns: {len(blockers) if isinstance(blockers, list) else 0}")
    print(f"major concerns: {len(majors) if isinstance(majors, list) else 0}")
    return 0


def workflow_next(machine: dict[str, Any], current: dict[str, Any]) -> int:
    state = overall_state(current)
    transitions = machine.get("transitions", {})
    candidates = transitions.get(state, []) if isinstance(transitions, dict) else []
    stale = stale_sections(current)
    if stale:
        print("stale sections should be resolved before broad polishing:")
        for name, section in stale:
            print(f"- {name} -> {section.get('route', 'section_loop')}")
    if not candidates:
        print(f"next overall state: none from {state}")
        return 0
    for index, candidate in enumerate(candidates):
        target = normalize_state(candidate)
        failures = guard_failures(machine, current, target)
        label = "guard ok" if not failures else "guard blocked"
        prefix = "next overall state" if index == 0 else "also allowed"
        print(f"{prefix}: {target} ({label})")
        for failure in failures:
            print(f"  - {failure}")
    return 0


def workflow_advance(
    root: Path,
    machine: dict[str, Any],
    current: dict[str, Any],
    raw_target: str,
) -> int:
    source = overall_state(current)
    target = normalize_state(raw_target)
    transitions = machine.get("transitions", {})
    allowed = [normalize_state(item) for item in transitions.get(source, [])] if isinstance(transitions, dict) else []
    if target not in allowed:
        print(f"error: transition not allowed: {source} -> {target}", file=sys.stderr)
        return 1
    failures = guard_failures(machine, current, target)
    if failures:
        print(f"guard failed for {target}:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    current.setdefault("overall", {})["state"] = target
    current["overall"]["previous_state"] = source
    write_mapping(root / CURRENT_REL, current)
    print(f"advanced: {source} -> {target}")
    return 0


def workflow_invalidate(
    root: Path,
    machine: dict[str, Any],
    current: dict[str, Any],
    artifact_id: str,
) -> int:
    artifact = artifact_id.strip()
    if not artifact:
        print("error: artifact id is empty", file=sys.stderr)
        return 2
    route = route_for_artifact(machine, artifact)
    changed: list[str] = []
    sections = current.get("sections", {})
    if not isinstance(sections, dict):
        print("error: workflow/current-state.yml sections must be a mapping", file=sys.stderr)
        return 1
    for name, section in sections.items():
        if not isinstance(section, dict):
            continue
        if section_depends_on(section, artifact):
            previous = section.get("state", "")
            section["state"] = "STALE"
            section["route"] = route
            section["stale_reason"] = f"{artifact} changed"
            section["previous_state"] = previous
            changed.append(str(name))
    if changed:
        write_mapping(root / CURRENT_REL, current)
        for name in changed:
            print(f"stale: {name} -> {route}")
    else:
        print(f"no dependent sections found for {artifact}")
    return 0


def workflow_route_review(
    root: Path,
    machine: dict[str, Any],
    current: dict[str, Any],
    raw_issue_class: str,
    *,
    apply: bool,
) -> int:
    issue_class = normalize_issue_class(raw_issue_class)
    if not issue_class:
        try:
            round_summary = load_mapping(root / ROUND_REL)
        except WorkflowError:
            round_summary = {}
        issue_class = normalize_issue_class(str(round_summary.get("issue_class", "")))
    issue_classes = machine.get("issue_classes", {})
    if not issue_class or not isinstance(issue_classes, dict) or issue_class not in issue_classes:
        print("error: unknown or missing issue class", file=sys.stderr)
        return 2
    issue_spec = issue_classes[issue_class]
    route_to = normalize_state(issue_spec.get("route_to", "")) if isinstance(issue_spec, dict) else ""
    if not route_to:
        print(f"error: issue class has no route_to: {issue_class}", file=sys.stderr)
        return 1
    print(f"issue class: {issue_class}")
    print(f"route to: {route_to}")
    if apply:
        current.setdefault("overall", {})["state"] = route_to
        current.setdefault("review", {})["last_issue_class"] = issue_class
        counters = current.setdefault("loop_counters", {})
        counters[issue_class] = int(counters.get(issue_class, 0)) + 1
        write_mapping(root / CURRENT_REL, current)
        print(f"applied route: {route_to}")
        max_rounds = int(machine.get("loop_policy", {}).get("max_autonomous_rounds_per_issue", 2))
        if counters[issue_class] > max_rounds:
            print(f"escalate: {issue_class} exceeded {max_rounds} autonomous rounds")
            return 1
    return 0


def guard_failures(machine: dict[str, Any], current: dict[str, Any], target: str) -> list[str]:
    guards = machine.get("guards", {})
    required = guards.get(target, []) if isinstance(guards, dict) else []
    values = current.get("guards", {}).get(target, {})
    if not isinstance(required, list):
        return [f"{target} guard definition is not a list"]
    if not isinstance(values, dict):
        return [f"{target} guard values are missing"]
    return [str(item) for item in required if values.get(str(item)) is not True]


def stale_sections(current: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    sections = current.get("sections", {})
    if not isinstance(sections, dict):
        return []
    return [
        (str(name), section)
        for name, section in sections.items()
        if isinstance(section, dict) and str(section.get("state", "")).upper() == "STALE"
    ]


def section_depends_on(section: dict[str, Any], artifact_id: str) -> bool:
    depends_on = section.get("depends_on", {})
    if not isinstance(depends_on, dict):
        return False
    for values in depends_on.values():
        if isinstance(values, str):
            iterable: Iterable[Any] = [values]
        elif isinstance(values, list):
            iterable = values
        else:
            continue
        for value in iterable:
            if artifact_ref_matches(str(value), artifact_id):
                return True
    return False


def artifact_ref_matches(reference: str, artifact_id: str) -> bool:
    return reference.split("@", 1)[0].strip() == artifact_id


def route_for_artifact(machine: dict[str, Any], artifact_id: str) -> str:
    prefix = artifact_id.split("-", 1)[0].upper()
    routes = machine.get("artifact_routes", {})
    if isinstance(routes, dict):
        return normalize_issue_class(str(routes.get(prefix, "section_loop")))
    return "section_loop"


def overall_state(current: dict[str, Any]) -> str:
    overall = current.get("overall", {})
    if isinstance(overall, dict):
        return normalize_state(str(overall.get("state", "SCOPED")))
    return "SCOPED"


def normalize_state(value: str) -> str:
    return value.strip().replace("-", "_").upper()


def normalize_issue_class(value: str) -> str:
    return value.strip().replace("-", "_").lower()


def load_mapping(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError(f"cannot read {path}: {exc}") from exc
    data: Any
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"{path} is not valid workflow YAML/JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowError(f"{path} must contain a mapping")
    return data


def write_mapping(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class WorkflowError(Exception):
    """Raised when workflow files cannot be loaded."""
