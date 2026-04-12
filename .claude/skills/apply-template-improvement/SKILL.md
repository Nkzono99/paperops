# apply-template-improvement

Use this skill when a template change has already been accepted and needs to be implemented safely.

## Objectives

1. Update the smallest possible set of root and `template/` files.
2. Preserve existing downstream expectations unless a migration is explicitly intended.
3. Refresh documentation and changelog entries alongside the implementation.
4. Run the local smoke checks after the change.

## Checklist

- Inspect the affected directories and scripts before editing.
- Update `CHANGELOG.md` for user-visible changes.
- Adjust the relevant docs in `docs/` or `template/docs/`.
- Run `make smoke`.
- Summarize any residual migration work for downstream repositories.
