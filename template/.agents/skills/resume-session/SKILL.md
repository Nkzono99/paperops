---
name: resume-session
description: Codex で執筆セッション開始時に状態を把握し、次の作業を提案する。
---

# resume-session

Codex で使う互換入口。実際の手順は `.claude/skills/resume-session/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `notes/handoff.md`、`notes/todo.md`、`notes/open-questions.md`、`manuscript/mirror/status.md` を優先して読む。
- 原稿編集前に ja/en のミラー状態を確認し、必要なら `make mirror-check` を実行する。
- ユーザーには、現在状態、次に安全に進める作業、未解決リスクを短く返す。
