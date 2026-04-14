# CLAUDE.md

Communicate with the user in **Japanese**.

This is the **template maintenance repository** for `paper-harness-template`.

## Architecture

Two-layer design:

- **Root layer**: template governance, reusable workflows, distribution automation, template-maintenance skills
- **`template/` layer**: per-paper scaffold that gets copied or published into individual `paper-<topic>` repositories

Do not confuse the two. Root-level files maintain the template itself; `template/` contains what downstream users receive.

## Key commands

```sh
make venv                      # create .venv with Python 3.11
make smoke                     # run lint-bib + mirror-check + collect-context against template/
make publish-scaffold-dry-run  # preview rsync of template/ into distribution repo
```

## Change workflow

1. Incoming issues arrive via structured issue forms (`template-feedback`, `skill-request`, `structure-change`).
2. Triage with `/triage-template-feedback`.
3. Implement with `/apply-template-improvement`.
4. Review with `/review-template-regression`.
5. Run `make smoke` before merging.
6. Update `CHANGELOG.md` for every user-visible change.

Read `docs/change-policy.md` and `docs/triage-rules.md` before landing changes.

## Rules

- Treat `template/AGENTS.md`, `template/CLAUDE.md`, `template/.claude/skills/`, and `template/scripts/` as **user-facing interfaces**. Changes to these require a migration note.
- Prefer additive changes over structural rewrites.
- Keep generated content out of version control.
- The distribution repository (`scripts/publish-scaffold.sh`) is a **publish target**, not the editing surface. Edit here, publish there.
- Always run `make smoke` after modifying anything under `template/`.

## Repository map

```
docs/                  architecture, change-policy, triage-rules, skill-catalog, distribution
.claude/skills/        triage-template-feedback, apply-template-improvement, review-template-regression
.github/workflows/     reusable-build, reusable-mirror-check, reusable-release, publish-scaffold
.github/ISSUE_TEMPLATE/ template-feedback, skill-request, structure-change
scripts/               publish-scaffold.sh
template/              full downstream scaffold (see template/CLAUDE.md)
```
