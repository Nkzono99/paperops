# paper-my-topic

Starter repository for a single paper project built from `paper-harness-template`.

## Before first use

1. Rename the repository and update this README.
2. Run `make venv` to create a local `.venv` with Python 3.11.
3. Copy `refs/local/locations.example.toml` to `refs/local/locations.toml`.
4. Replace the placeholder workflow references in `.github/workflows/*.yml` with your actual `paper-harness-template` repository path.
5. Fill in `docs/project-brief.md`, `docs/target-venue.md`, and `docs/contribution-claims.md`.

## Core workflow

1. Start with `resume-session`.
2. Write or revise in `manuscript/ja/`.
3. Mirror the necessary blocks into `manuscript/en/`.
4. Capture progress in `notes/`.
5. Run `make ci` before sharing major changes.

The local workflow prefers `.venv/bin/python` and otherwise falls back to `python3.11`.

## Template feedback

If you find repeated harness friction, route reusable improvements back to the source repository `Nkzono99/paper-harness-template`.
Do not treat the distribution template repository as the primary issue tracker unless your team maintains its own forked source of truth.

## Directory highlights

- `manuscript/`: bilingual source, shared style assets, and mirror-control files
- `refs/`: reference knowledge, bibliographies, excerpts, and local path aliases
- `notes/`: session continuity and decision tracking
- `.claude/`: project-local Claude settings, hooks, and skills
- `scripts/`: lightweight validation and packaging helpers
