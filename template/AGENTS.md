# AGENTS

This repository is a writing harness for a bilingual research paper.

## Start here

1. Read `docs/project-brief.md`.
2. Read `notes/session-context.md`, `notes/handoff.md`, and `notes/todo.md`.
3. Check `manuscript/mirror/status.md` before editing manuscript text.

## Ground rules

- Japanese content is the source of truth unless `manuscript/mirror/status.md` says otherwise.
- Preserve `% block: ...` identifiers in all mirrored sections.
- Keep `refs/` organized as a knowledge layer, not a raw PDF dump.
- Never commit personal absolute paths; use `refs/local/locations.example.toml` plus an ignored local override.
- Update `notes/` before ending a working session.

## Standard commands

- `make build-ja`
- `make build-en`
- `make mirror-check`
- `make lint-bib`
- `make ci`
