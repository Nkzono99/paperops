# Managed Harness Overlays Design

## Goal

Project repositories should be able to optimize paperops behavior without editing files that `paperops` owns and updates. Updates should remain simple: upstream-managed harness files advance through `pops update-paperops`, project-specific behavior lives in overlay files, and unavoidable divergences are recorded as explicit detached forks.

## Problem

Current managed update boundaries mix two concerns:

- Upstream harness defaults: agent guidance, skills, scripts, workflow machine defaults, and section contract defaults.
- Project adaptation: paper type, venue expectations, section emphasis, extra guards, local make targets, and project-specific agent instructions.

When project authors edit distributed harness files directly, `update-paperops` can only report changed managed files and leave them untouched or overwrite them with `--force`. That makes routine updates noisy and encourages long-lived local drift.

## Ownership Model

paperops should treat scaffold files as three ownership classes.

| Class | Owner | Update behavior | Examples |
| --- | --- | --- | --- |
| Managed core | paperops | Updated by `pops update-paperops`; local changes are drift | `AGENTS.md`, `CLAUDE.md`, `Makefile`, `scripts/`, managed skills, harness contract defaults, workflow machine defaults |
| Project overlay | project repo | Never overwritten by `update-paperops`; read together with managed defaults | `manuscript/writing-profile.yml`, project contract overlays, project workflow overlay, project agent guidance, project make targets |
| Detached fork | project repo | Excluded from automatic update after explicit record | A managed file that the project intentionally owns after `pops detach` or equivalent |

The normal path is managed core plus project overlay. Detached fork is an escape hatch, not the default extension mechanism.

## Directory Direction

Introduce a clearer split under `_paperops/`.

```text
_paperops/defaults/
  contracts/          paperops-managed default contracts
  workflow/           paperops-managed default workflow machine and guard defaults

_paperops/contracts/  project-owned contract overlays or effective project contracts
_paperops/workflow/   project-owned current state and project overlay files
```

The first implementation slice may keep existing paths working, but new docs and new scaffold should move toward this split.

## Merge Semantics

Readers that need contracts or workflow configuration should load data in this order:

1. Managed base from `_paperops/defaults/<kind>/`.
2. Project overlay from `_paperops/<kind>/`.
3. Local ignored files only for machine-specific values where applicable.

Project overlays should be partial. They only declare project-specific additions or overrides, so upstream defaults can evolve without forcing every project to copy full files.

The effective configuration should be inspectable. A future `pops` command can show which value came from managed base versus project overlay, but the first implementation can document the merge contract and protect the update boundary.

## Managed Update Rules

`pops update-paperops` should avoid broad ownership globs for extension areas. Instead:

- Update only paperops-owned paths.
- Leave project-owned overlay paths outside the update plan.
- Report local changes to managed files as drift.
- Offer a narrow path for project-owned additions, such as project skills or project make targets, without putting them under broad managed globs.

This means `.agents/*` and `.claude/*` should eventually become narrower managed patterns or explicit managed path manifests, so project-specific skills are not accidentally treated as upstream-owned.

## Extension Points

Project repositories should customize through explicit extension points:

- `manuscript/writing-profile.yml` for paper type, venue, language, and prose preferences.
- `_paperops/contracts/` for contract overlays.
- `_paperops/workflow/project.yml` for additional guards or project-specific workflow policy.
- `AGENTS.project.md` and `CLAUDE.project.md` for project guidance loaded by the managed root guidance.
- `Makefile.project` for tracked project targets and `Makefile.local` for ignored machine-local targets.
- Project skills under a reserved non-managed naming convention, such as `.agents/skills/project-*` and `.claude/skills/project-*`.

## Detached Forks

When a project must edit a managed core file, the user should make that explicit. The future CLI shape can be:

```sh
pops detach _paperops/defaults/workflow/machine.yml --reason "venue-specific review loop"
pops detach list
```

Detached files should be recorded in `.pops/manifest.toml` with path, reason, source scaffold version, and timestamp. `update-paperops` should skip detached files and report that they need manual rebase when upstream changes.

## Migration Policy

Moving managed defaults from `_paperops/contracts/` and `_paperops/workflow/` into `_paperops/defaults/` is a breaking layout change and should be represented as a migration item. The migration must preserve project-specific content:

- Install fresh managed defaults under `_paperops/defaults/` through `update-paperops`.
- Leave existing `_paperops/contracts/` or `_paperops/workflow/` files in place as project overlays until explicitly reviewed.
- Never delete project content during automatic migration.

This aligns with the checkpoint-based migration model: each release carries only the migration from the previous checkpoint to itself, and older migrations are reached by `update-paperops --apply-chain`.

## Testing Expectations

Tests should cover:

- Managed update planning excludes project overlay files.
- Managed update planning still reports drift in managed core files.
- New scaffold contains the documented overlay extension points.
- Migration planning does not delete edited project files.
- Existing commands keep working during the compatibility window.

## Initial Implementation Slice

The first slice should avoid a large rewrite. It should:

1. Add project extension files to the template.
2. Narrow managed update rules enough to protect project-owned extension files.
3. Document the ownership model in `docs/cli.md`, `docs/current-specification.md`, and downstream guidance.
4. Add tests for update boundaries and extension files.
5. Add a migration note for the future `_paperops/defaults/` move without forcing that move in the same change unless the implementation remains small.
