# Glob: manuscript/**/*.tex

## Manuscript editing rules

- Preserve `% block: ...` identifiers. Never remove, rename, or renumber them.
- Japanese (`ja/`) is the source of truth unless `manuscript/mirror/status.md` says otherwise.
- After editing a ja/ section, note the affected block IDs for later `/sync-ja-en`.
- Do not edit files under `manuscript/shared/figures/generated/` directly.
- Keep `\input` paths relative to the manuscript root.
