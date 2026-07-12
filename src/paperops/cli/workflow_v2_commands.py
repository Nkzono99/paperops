"""Thin CLI adapters for the typed workflow kernel."""

from __future__ import annotations

import json
import os
from pathlib import Path

from paperops.workflow_v2.catalog import load_workflow_catalog
from paperops.workflow_v2.graph import build_dependency_graph, plan_workflow_impact
from paperops.workflow_v2.profile import load_workflow_profile
from paperops.workflow_v2.projection import project_workflow_status


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def workflow_v2_status(root: Path, *, json_output: bool) -> int:
    profile = load_workflow_profile(root)
    snapshot = load_workflow_catalog(root)
    result = project_workflow_status(snapshot, build_dependency_graph(snapshot), profile)
    payload = result.to_dict()
    if json_output:
        print(_canonical(payload), end="")
    else:
        print(f"workflow stage: {result.stage}")
        print(f"review: {result.review_axis}")
        print(f"submission: {result.submission_axis}")
        print(f"stale impacts: {len(result.stale_impacts)}")
    return 1 if any(row.severity == "error" for row in result.reasons) else 0


def workflow_v2_plan(root: Path, *, changed: tuple[str, ...], issues: tuple[str, ...], json_output: bool) -> int:
    load_workflow_profile(root)
    graph = build_dependency_graph(load_workflow_catalog(root))
    result = plan_workflow_impact(graph, changed_ids=changed, issue_ids=issues)
    payload = result.to_dict()
    directory = root / ".paperops/workflow/plans" / result.plan_id
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".plan.{os.getpid()}.tmp"
    temporary.write_text(_canonical(payload), encoding="utf-8")
    os.replace(temporary, directory / "plan.json")
    if json_output:
        print(_canonical(payload), end="")
    else:
        print(f"workflow plan: {result.plan_id}")
        print(f"ready: {'yes' if result.ready else 'no'}")
        for impact in result.impacts:
            if impact.impact != "unaffected":
                print(f"- {impact.target_id}: {impact.impact} ({impact.relation})")
    return 0 if result.ready else 1
