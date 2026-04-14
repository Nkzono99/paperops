# CLAUDE.md

Communicate with the user in **Japanese**.

This is a **bilingual paper writing harness**. Japanese and English manuscripts are tracked as block-level mirrors.

## Session protocol

### Start

1. Run `/resume-session`.
2. Read `docs/project-brief.md` and `notes/session-context.md`.
3. Check `manuscript/mirror/status.md` before editing manuscript text.

### End

1. Run `/note-writing-session`.
2. Refresh `notes/handoff.md` and `notes/todo.md`.
3. Run `make ci` if manuscript structure or references changed.

## Key commands

```sh
make venv           # create .venv with Python 3.11
make build-ja       # compile Japanese manuscript (or structural validation)
make build-en       # compile English manuscript (or structural validation)
make lint-bib       # validate bibliography entries
make mirror-check   # detect block-level drift between ja/ and en/
make collect-context # aggregate notes into session-context.generated.md
make export-arxiv   # bundle English manuscript for arXiv submission
make ci             # lint-bib + mirror-check + build-ja + build-en
```

## Rules

### Source of truth

- `manuscript/ja/` is the scientific source of truth unless `manuscript/mirror/status.md` explicitly says otherwise.
- Preserve `% block: ...` identifiers in all mirrored sections. Never remove or renumber them.

### Protected files

These files are guarded by hooks and must not be edited directly:

- `manuscript/shared/figures/generated/**` -- regenerate via scripts, not manual edits
- `refs/local/locations.toml` -- personal paths, never commit
- `manuscript/shared/style/journal.cls` -- requires explicit user permission

### References

- `refs/` is a **knowledge layer**, not a PDF dump. Prefer curated summaries (`refs/summaries/`) over raw files.
- Keep citation keys stable after first manuscript use.
- Use `refs/local/locations.example.toml` as a template; the real `locations.toml` is gitignored.

### Notes

- End each session by updating `notes/session-context.md`, `notes/handoff.md`, and `notes/todo.md`.
- Record durable decisions in `notes/decision-log.md`, not only in chat history.

### Mirror sync

- Use `/sync-ja-en` for block-level synchronization.
- Never overwrite both languages blindly. Check `manuscript/mirror/status.md` and `change-queue.md` first.
- Terminology is pinned in `manuscript/mirror/terminology.yml`.

## Available skills

| Skill | Purpose |
|-------|---------|
| `/resume-session` | Summarize current state and propose next steps |
| `/note-writing-session` | Record session progress and refresh handoff files |
| `/sync-ja-en` | Synchronize Japanese and English blocks |
| `/update-refs` | Validate bibliography and reference knowledge alignment |
| `/improve-writing-harness` | Identify and fix project-local friction |
| `/raise-template-feedback` | Escalate reusable improvements to upstream template |
| `/resolve-local-paths` | Resolve local path aliases from `refs/local/` |

## Repository map

```
manuscript/
  ja/              Japanese source (sections with % block: IDs)
  en/              English mirror (sections with matching block IDs)
  shared/          figures, tables, bib, style, build output
  mirror/          map.toml, terminology.yml, status.md, change-queue.md
refs/              knowledge layer: papers, summaries, bib, excerpts, local paths
notes/             session continuity: handoff, todo, decision-log, sessions/
scripts/           build, lint, mirror-check, export, context collection
docs/              project-brief, target-venue, contribution-claims, policies
.claude/           settings.json (hooks), skills/
```

## Template feedback

If you find repeated harness friction that would benefit other paper repositories, use `/raise-template-feedback` to route it to the upstream `Nkzono99/paper-harness-template`.
