"""P3 readiness projection for v2-authoritative workflow impacts."""

from __future__ import annotations

import tomllib
from pathlib import Path

from paperops.compiler.safe_fs import SafeProjectReader
from paperops.compiler.types import CompileFinding
from paperops.workflow_v2.mutation import load_documents


def workflow_compile_findings(root: Path, section_ids: tuple[str, ...]) -> tuple[CompileFinding, ...]:
    with SafeProjectReader(root) as reader:
        manifest = reader.read_optional_file(".pops/manifest.toml")
    if manifest is None:
        return ()
    try:
        data = tomllib.loads(manifest[0].decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("workflow authority manifest is invalid") from exc
    workflow = data.get("workflow", {})
    mode = workflow.get("mode", "legacy") if isinstance(workflow, dict) else "legacy"
    if mode != "v2-authoritative":
        return ()
    selected = set(section_ids)
    findings = []
    for ref in load_documents(root).values():
        document = ref.document
        if document.get("record_type") != "workflow_issue" or document.get("status") == "closed":
            continue
        impacts = document.get("impacts", [])
        if not isinstance(impacts, list):
            continue
        for index, impact in enumerate(impacts):
            if not isinstance(impact, dict) or impact.get("state") != "open" or impact.get("target_id") not in selected:
                continue
            findings.append(
                CompileFinding(
                    code="compile.workflow_open_impact",
                    pointer=f"/workflow/issues/{document.get('id', 'unknown')}/impacts/{index}",
                    message="The selected compile scope has an unresolved workflow impact.",
                )
            )
    return tuple(sorted(findings, key=lambda row: (row.pointer, row.code)))
