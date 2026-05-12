---
name: feedback-paper-harness
description: Codex で再利用可能な改善を上流 paperops にフィードバックする。
---

# feedback-paper-harness

Codex で使う互換入口。実際の手順は `.claude/skills/feedback-paper-harness/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 問題、再現手順、影響度、提案変更、下流での影響範囲を分けて整理する。
- `pops feedback` が使える場合は、Issue 本文案の初期生成に使う。
- GitHub CLI または GitHub app が使える場合は `Nkzono99/paperops` に構造化 Issue として起票する。
- 起票できない環境では、Issue 本文案を作成してユーザーに渡す。
