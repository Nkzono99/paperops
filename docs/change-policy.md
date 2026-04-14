# Change Policy

## Goals

Template changes should improve multiple paper repositories, stay backwards-conscious, and remain easy to adopt.

## Decision rules

1. Prefer additive changes over structural rewrites.
2. Treat `template/AGENTS.md`, `template/CLAUDE.md`, `.claude/skills/`, and `scripts/` as user-facing interfaces.
3. Require a documented migration note for any change that would force downstream repos to rename files, move directories, or rewrite hooks.
4. Keep generated content out of version control unless it is a checked-in starter artifact.
5. Treat the distribution repository as a publish target. Do not make it the primary editing surface.

## Release expectations

- Update [`CHANGELOG.md`](/home/b/b36291/large1/Github/paper-harness-template/CHANGELOG.md) for every user-visible improvement.
- If a change affects downstream setup, update [`README.md`](/home/b/b36291/large1/Github/paper-harness-template/README.md) and the relevant file inside `template/docs/`.
- When in doubt, open a `template-feedback` issue first and triage scope before landing the change.
