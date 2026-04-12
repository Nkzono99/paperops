# sync-ja-en

Use this skill to keep the Japanese and English manuscripts aligned at the block level.

## Read first

- `manuscript/mirror/map.toml`
- `manuscript/mirror/terminology.yml`
- `manuscript/mirror/status.md`
- `manuscript/mirror/change-queue.md`

## Responsibilities

1. Treat Japanese as the source of truth unless `status.md` says otherwise.
2. Compare matching files block by block using `% block: ...` identifiers.
3. Update English text only for the blocks requested or clearly outdated.
4. If the English text changes scientific meaning, reflect that change back into Japanese or log it in `change-queue.md`.
5. Refresh `status.md` after meaningful sync work.

## Aids

- `templates/drift-report.md`
- `scripts/sync_blocks.py`

Never overwrite both languages blindly. Preserve block IDs and scientific intent.
