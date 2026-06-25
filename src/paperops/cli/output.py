"""Small output helpers shared by CLI commands."""

from __future__ import annotations

from pathlib import Path

from paperops.cli.models import CopyPlan
from paperops.cli.runtime import uvx_pops_command


def managed_update_surface(rel: str) -> str:
    if rel in {"AGENTS.md", "CLAUDE.md"}:
        return "agent guidance"
    if rel == "Makefile":
        return "make workflow"
    if rel == "TROUBLESHOOTING.md":
        return "operator docs"
    if rel.startswith("contracts/"):
        return "section contract"
    if rel.startswith("scripts/"):
        return "validation/build script"
    if rel.startswith(".agents/skills/"):
        return "Codex skill entry"
    if rel.startswith(".agents/"):
        return "Codex agent config"
    if rel.startswith(".claude/skills/"):
        return "Claude skill source"
    if rel.startswith(".claude/rules/"):
        return "Claude rule"
    if rel.startswith(".claude/"):
        return "Claude agent config"
    if rel.startswith(".github/ISSUE_TEMPLATE/"):
        return "issue template"
    if rel == ".github/PULL_REQUEST_TEMPLATE.md":
        return "pull request template"
    return "managed harness file"


def print_next_steps(target: Path) -> None:
    print("Next steps:")
    print("  cd " + str(target))
    print("  " + uvx_pops_command("doctor"))
    print("  make venv  # optional: create a project Python environment")


def print_copy_summary(plan: CopyPlan) -> None:
    print(f"  copied: {len(plan.missing)}")
    print(f"  already present: {len(plan.unchanged)}")
    print(f"  different and left untouched: {len(plan.changed)}")
    print(f"  excluded: {len(plan.excluded)}")


def print_update_plan(plan: CopyPlan) -> None:
    print("Paperops update plan:")
    print(f"  missing managed files: {len(plan.missing)}")
    for rel in plan.missing[:20]:
        print(f"    + {rel} [{managed_update_surface(rel)}]")
    if len(plan.missing) > 20:
        print(f"    ... {len(plan.missing) - 20} more")
    print(f"  changed managed files: {len(plan.changed)}")
    if plan.changed:
        print(
            "    meaning: target file differs from the scaffold source and "
            "is left untouched by --apply."
        )
    for rel in plan.changed[:20]:
        print(f"    ! {rel} [{managed_update_surface(rel)}]")
    if len(plan.changed) > 20:
        print(f"    ... {len(plan.changed) - 20} more")
    print(f"  unchanged managed files: {len(plan.unchanged)}")
    if plan.missing or plan.changed:
        print("  update guidance:")
        if plan.missing:
            print("    + missing files can be added with --apply.")
        if plan.changed:
            print(
                "    ! changed files need manual review; use --apply --force "
                "only when local edits may be replaced."
            )
            print("    narrow review with --only <path-or-prefix> when useful.")
        print(
            "    project content remains outside this plan: README.md, notes/, "
            "manuscript/, refs/, submission/."
        )
