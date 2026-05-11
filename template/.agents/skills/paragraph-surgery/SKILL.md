---
name: paragraph-surgery
description: Codex で段落単位の流れ、topic sentence、stress position を整える。
---

# paragraph-surgery

Codex で使う互換入口。実際の手順は `.claude/skills/paragraph-surgery/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 段落を context / claim / evidence / warrant / limitation / transition に分類する。
- 科学的意味を変える場合は先に計画を示す。
- 本文を編集したら `make mirror-check`、必要なら `/sync-ja-en` を実行する。
