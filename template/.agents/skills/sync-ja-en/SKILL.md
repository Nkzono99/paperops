---
name: sync-ja-en
description: Codex で日本語と英語の原稿をブロックレベルで同期する。
---

# sync-ja-en

Codex で使う互換入口。実際の手順は `.claude/skills/sync-ja-en/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `% block: ...` ID を保持し、片側を盲目的に上書きしない。
- 同期前後に `manuscript/mirror/status.md` と `manuscript/mirror/change-queue.md` を確認する。
- 必要に応じて `.claude/skills/sync-ja-en/scripts/sync_blocks.py` を実行し、最後に `make mirror-check` を実行する。
