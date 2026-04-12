# Agent Operating Rules

## Session start

1. Run `resume-session`.
2. Read `docs/project-brief.md` and `notes/session-context.md`.
3. Check `manuscript/mirror/status.md` before editing bilingual content.

## Editing rules

- Do not edit `manuscript/shared/figures/generated/` directly.
- Do not commit `refs/local/locations.toml`.
- Avoid changing `manuscript/shared/style/journal.cls` unless the user explicitly requests a class-level update.

## Session end

1. Run `note-writing-session`.
2. Refresh `notes/handoff.md`.
3. Refresh `notes/todo.md`.
4. Run `make ci` if manuscript structure or references changed.
