# CLAUDE.md

Communicate with the user in **Japanese**.

This is a **bilingual paper writing harness**. Japanese and English manuscripts are tracked as block-level mirrors.

## Session protocol

### Start

1. Run `/resume-session`.
2. Read `docs/project-brief.md` if this is the first session.
3. Check `manuscript/mirror/status.md` before editing manuscript text.

### End

1. Run `/note-writing-session`.
2. Run `make ci` if manuscript structure or references changed.

### On compaction

Session context is automatically re-injected via PreCompact hook. After compaction, re-read `notes/handoff.md` and `notes/todo.md` if the task requires continuity.

## Key commands

```sh
make venv           # create .venv with Python 3.11
make build-ja       # compile Japanese manuscript (or structural validation)
make build-en       # compile English manuscript (or structural validation)
make lint-bib       # validate bibliography entries
make mirror-check   # detect block-level drift between ja/ and en/
make ci             # lint-bib + mirror-check + build-ja + build-en
make export-arxiv   # bundle English manuscript for arXiv submission
```

## Rules

- `manuscript/ja/` is the scientific source of truth unless `manuscript/mirror/status.md` says otherwise.
- Preserve `% block: ...` identifiers. Never remove or renumber them.
- Do not edit protected files directly: `manuscript/shared/figures/generated/**`, `refs/local/locations.toml`, `manuscript/shared/style/journal.cls` (hooks enforce this).
- `refs/` is a **knowledge layer**. Prefer curated summaries over raw PDFs. Keep citation keys stable.
- Use `/sync-ja-en` for mirror sync. Never overwrite both languages blindly.
- End each session by updating `notes/handoff.md` and `notes/todo.md`.
- Record durable decisions in `notes/decision-log.md`.

File-specific rules are in `.claude/rules/` and load automatically when editing matching paths.

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
manuscript/ja/       Japanese source (sections with % block: IDs)
manuscript/en/       English mirror (matching block IDs)
manuscript/shared/   figures, tables, bib, style, build output
manuscript/mirror/   map.toml, terminology.yml, status.md, change-queue.md
refs/                knowledge layer: papers, summaries, bib, excerpts, local
notes/               session continuity: handoff, todo, decision-log, sessions/
scripts/             build, lint, mirror-check, export, context collection
docs/                project-brief, target-venue, contribution-claims, policies
.claude/             settings.json (hooks + permissions), skills/, rules/
```

## Template feedback

If you find repeated harness friction, use `/raise-template-feedback` to route it to `Nkzono99/paper-harness-template`.
