---
name: note-writing-session
description: Codex で作業セッション終了時に handoff と todo を更新する。
---

# note-writing-session

Codex で使う互換入口。実際の手順は `.claude/skills/note-writing-session/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `notes/handoff.md`、`notes/todo.md`、必要に応じて `notes/decision-log.md` を更新する。
- データ、解析環境、図表生成、共有 artifact が変わった場合は `notes/reproducibility.md` を更新する。
- 恒久的な判断と一時的な作業メモを混ぜない。
- 原稿構造、参考文献、ミラー状態を変えた場合は `make ci` または該当チェックを実行する。
