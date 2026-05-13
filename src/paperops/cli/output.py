"""Small output helpers shared by CLI commands."""

from __future__ import annotations

from pathlib import Path

from paperops.cli.models import CopyPlan
from paperops.cli.runtime import uvx_pops_command


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
        print(f"    + {rel}")
    if len(plan.missing) > 20:
        print(f"    ... {len(plan.missing) - 20} more")
    print(f"  changed managed files: {len(plan.changed)}")
    for rel in plan.changed[:20]:
        print(f"    ! {rel}")
    if len(plan.changed) > 20:
        print(f"    ... {len(plan.changed) - 20} more")
    print(f"  unchanged managed files: {len(plan.unchanged)}")
