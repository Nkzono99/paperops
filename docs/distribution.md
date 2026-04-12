# Distribution

This repository is the source of truth for the paper-writing harness.
The downstream GitHub template repository is a published artifact generated from `template/`.

## Repository roles

- Source repository: `Nkzono99/paper-harness-template`
  - Maintains docs, issue forms, reusable workflows, and the scaffold source under `template/`
- Distribution repository: `Nkzono99/paper-harness-scaffold-template`
  - Contains only the scaffold at repository root and is marked as a GitHub template repository

## Publishing model

Changes are made here first.
The `Publish Scaffold` workflow then syncs `template/` into the distribution repository root with `rsync`.

## Required GitHub Actions configuration

Set these in the source repository:

- Actions variable `PUBLISH_TARGET_REPO`
  - Example: `Nkzono99/paper-harness-scaffold-template`
- Actions secret `PUBLISH_TEMPLATE_TOKEN`
  - A token with access to push to the distribution repository

## Operational rules

- Do not edit the distribution repository by hand.
- Route issues and improvements back to the source repository.
- If the distribution repository must be patched directly in an emergency, mirror the same change back here immediately.
