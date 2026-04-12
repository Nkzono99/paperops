# paper-harness-template

Reusable harness for AI-assisted paper writing.

This repository is structured as the `paper-template` side described in `SPEC.md`.
It contains two layers:

- repository-level assets for maintaining the template itself
- a full per-paper scaffold under [`template/`](/home/b/b36291/large1/Github/paper-harness-template/template)

## Repository layout

- [`.github/workflows/`](/home/b/b36291/large1/Github/paper-harness-template/.github/workflows): reusable GitHub Actions workflows callable from downstream paper repositories
- [`.github/ISSUE_TEMPLATE/`](/home/b/b36291/large1/Github/paper-harness-template/.github/ISSUE_TEMPLATE): structured issue forms for feedback, skill requests, and structure changes
- [`.claude/skills/`](/home/b/b36291/large1/Github/paper-harness-template/.claude/skills): skills for template triage and maintenance
- [`docs/`](/home/b/b36291/large1/Github/paper-harness-template/docs): template architecture, change policy, and triage rules
- [`template/`](/home/b/b36291/large1/Github/paper-harness-template/template): ready-to-copy scaffold for an individual `paper-<topic>` repository
- [`docs/distribution.md`](/home/b/b36291/large1/Github/paper-harness-template/docs/distribution.md): publish model for syncing `template/` into a separate GitHub template repository

## Quick start

1. Publish `template/` into the separate distribution repository, or copy it manually into a new repository such as `paper-my-topic/`.
2. Run `make venv` to create a local `.venv` with Python 3.11.
3. Rename the repository and update the following starter files:
   - `README.md`
   - `docs/project-brief.md`
   - `docs/target-venue.md`
   - `docs/contribution-claims.md`
   - `refs/local/locations.toml` from `refs/local/locations.example.toml`
4. Add your manuscript content to `manuscript/ja` first, then sync targeted sections into `manuscript/en`.
5. Run `make ci` in the paper repository to lint bibliographies, validate mirror coverage, and exercise the build harness.

## What the scaffold optimizes for

- `refs/` as a shared knowledge layer instead of a raw PDF dump
- `notes/` as session handoff and continuity state
- Japanese and English manuscripts tracked as block-level mirrors
- reusable maintenance workflows for the template itself
- project-local Claude skills, hooks, and operating rules

## Distribution

If you want GitHub's `Use this template` flow, keep this repository as the source of truth and publish `template/` into a second repository whose root contains only the scaffold.
This repository includes [`scripts/publish-scaffold.sh`](/home/b/b36291/large1/Github/paper-harness-template/scripts/publish-scaffold.sh) and [`.github/workflows/publish-scaffold.yml`](/home/b/b36291/large1/Github/paper-harness-template/.github/workflows/publish-scaffold.yml) for that sync path.

## Validation model

The template ships lightweight local checks instead of assuming a full TeX environment.
`scripts/build-ja.sh` and `scripts/build-en.sh` compile with `latexmk` when available, and otherwise fall back to structural validation so CI can still exercise the writing harness on a clean runner.
The intended local setup is `python3.11` inside a repo-local `.venv`.

## Upstream references

The hook and settings layout follows Anthropic's Claude Code documentation for project settings and hooks, and the GitHub automation files follow GitHub's reusable workflow and issue form docs:

- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations
- https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
