# Architecture

This repository separates template maintenance concerns from per-paper authoring concerns.

## Layers

### 1. Template repository layer

The repository root owns the assets that every downstream paper repository should share:

- reusable GitHub workflows
- issue forms for template improvement
- template-maintainer skills
- changelog and governance docs

This layer is intentionally small and stable. Its job is to evolve the harness safely.

### 2. Per-paper scaffold layer

[`template/`](/home/b/b36291/large1/Github/paper-harness-template/template) contains the complete structure for an individual manuscript repository.
That scaffold includes:

- manuscript source split into `ja/` and `en/`
- a mirror-control layer under `manuscript/mirror/`
- reference knowledge under `refs/`
- session continuity notes under `notes/`
- project-local Claude skills and hooks
- lightweight scripts for build, lint, export, and note collection

## Design principles

- Keep the manuscript repository self-describing.
- Track bilingual drift explicitly instead of relying on ad hoc translation.
- Preserve local paths through aliases and ignored config files.
- Push reusable automation into the template repository, not every paper repository.
- Keep validation fast enough to run in interactive sessions and CI.
