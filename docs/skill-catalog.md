# Skill Catalog

## Template maintenance skills

### `triage-template-feedback`

Reads incoming feedback and decides whether the fix belongs in:

- `template/` structure
- root documentation
- reusable workflows
- template-maintainer skills
- project-local customization guidance

### `apply-template-improvement`

Implements an accepted template improvement while preserving downstream compatibility and documenting the change.

### `review-template-regression`

Checks whether a proposed template change weakens mirror tracking, note continuity, refs organization, or safety protections.

## Project-local skills included in the scaffold

The downstream scaffold ships these skills in `template/.claude/skills/`:

- `resume-session`
- `sync-ja-en`
- `note-writing-session`
- `improve-writing-harness`
- `raise-template-feedback`
- `update-refs`
- `resolve-local-paths`

## Distribution automation

The repository also ships a publish helper:

- `scripts/publish-scaffold.sh`: syncs `template/` into a distribution repository root with `rsync`
