"""Project-state migrations for ``pops migrate``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


LEGACY_INTERNAL_DIRS = (
    "contracts",
    "workflow",
    "refs",
    "evidence",
    "claims",
    "review",
    "requests",
    "notes",
)


@dataclass(frozen=True)
class Migration:
    migration_id: str
    title: str
    checkpoint: str
    summary: str
    moves: tuple[tuple[str, str], ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationPlan:
    migration: Migration
    moves: tuple[tuple[str, str], ...]
    conflicts: tuple[tuple[str, str], ...]
    skipped: tuple[str, ...]


INTERNAL_LAYOUT_MIGRATION = Migration(
    migration_id="M0-0001",
    title="Move legacy top-level paperops state into _paperops",
    checkpoint="v0 checkpoint for the _paperops internal layout",
    summary=(
        "Moves AI/harness-owned paper state out of the human-facing project "
        "root so future releases can drop long-lived legacy path fallback."
    ),
    moves=tuple((f"{name}/", f"_paperops/{name}/") for name in LEGACY_INTERNAL_DIRS),
)

DEFAULTS_SPLIT_MIGRATION = Migration(
    migration_id="M0-0002",
    title="Split managed defaults from project overlays",
    checkpoint="v0 checkpoint for _paperops/defaults",
    summary=(
        "Keeps project-specific contract and workflow edits as overlays while "
        "installing paperops-managed defaults under _paperops/defaults via "
        "update-paperops."
    ),
    moves=(),
    notes=(
        "Run `pops update-paperops --apply` to add missing _paperops/defaults files.",
        "Leave existing _paperops/contracts/* and _paperops/workflow/machine.yml "
        "as project overlays until you explicitly review them.",
        "No files are deleted or moved by this migration item.",
    ),
)

TYPED_RESULTS_HIERARCHY_MIGRATION = Migration(
    migration_id="M0-0003",
    title="Adopt the typed Results hierarchy model",
    checkpoint="v0 checkpoint for typed editorial state",
    summary=(
        "Introduces project-owned _paperops/model/editorial/results-hierarchy.yml "
        "while retaining the legacy Markdown reader for existing projects."
    ),
    moves=(),
    notes=(
        "New projects receive the typed starter model from pops init.",
        "Existing projects may keep the legacy storyline.md Results hierarchy during the compatibility checkpoint.",
        "Adopt the typed file manually from the starter schema, then run make section-contract-check.",
    ),
)

EDITORIAL_MODEL_SCHEMA_KERNEL_MIGRATION = Migration(
    migration_id="M0-0004",
    title="Adopt the Editorial Model schema kernel",
    checkpoint="v0 checkpoint for the PaperOps 2 P1-A schema kernel",
    summary=(
        "Guides existing projects to adopt the project-owned Editorial Model "
        "without generating or overwriting project-owned state."
    ),
    moves=(),
    notes=(
        "Run `pops update-paperops --apply` to receive the managed registry, schemas, and checker.",
        "Create _paperops/model/editorial/editorial-model.yml manually; migration apply never creates project-owned state.",
        "Use `make schema-check` for advisory checks, then run the documented explicit `--strict` command successfully.",
        "Keep the legacy controlled view through P2; do not switch authority or remove it during this migration.",
    ),
)


def registered_migrations() -> tuple[Migration, ...]:
    return (
        INTERNAL_LAYOUT_MIGRATION,
        DEFAULTS_SPLIT_MIGRATION,
        TYPED_RESULTS_HIERARCHY_MIGRATION,
        EDITORIAL_MODEL_SCHEMA_KERNEL_MIGRATION,
    )


def get_migration(migration_id: str) -> Migration | None:
    normalized = migration_id.strip().upper()
    for migration in registered_migrations():
        if migration.migration_id == normalized:
            return migration
    return None


def find_migration_root(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".pops" / "manifest.toml").exists():
            return candidate
        if has_modern_or_legacy_project_markers(candidate):
            return candidate
    return None


def has_modern_or_legacy_project_markers(candidate: Path) -> bool:
    required = ["manuscript", "scripts", "Makefile"]
    if not all((candidate / marker).exists() for marker in required):
        return False
    return (candidate / "_paperops").exists() or any(
        (candidate / directory).exists() for directory in LEGACY_INTERNAL_DIRS
    )


def plan_migration(root: Path, migration: Migration) -> MigrationPlan:
    moves: list[tuple[str, str]] = []
    conflicts: list[tuple[str, str]] = []
    skipped: list[str] = []
    for source_rel, target_rel in migration.moves:
        source = root / source_rel.rstrip("/")
        target = root / target_rel.rstrip("/")
        if source.exists() and target.exists():
            conflicts.append((source_rel, target_rel))
        elif source.exists():
            moves.append((source_rel, target_rel))
        else:
            skipped.append(source_rel)
    return MigrationPlan(
        migration=migration,
        moves=tuple(moves),
        conflicts=tuple(conflicts),
        skipped=tuple(skipped),
    )


def apply_migration(root: Path, plan: MigrationPlan, *, dry_run: bool) -> None:
    if dry_run or plan.conflicts:
        return
    (root / "_paperops").mkdir(exist_ok=True)
    for source_rel, target_rel in plan.moves:
        source = root / source_rel.rstrip("/")
        target = root / target_rel.rstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
