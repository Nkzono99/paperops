---
name: raise-template-feedback
description: Codex で再利用可能な改善を上流 paper-harness-template に起票する。
---

# raise-template-feedback

Codex で使う互換入口。実際の手順は `.claude/skills/raise-template-feedback/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 問題、再現手順、影響度、提案変更、下流での影響範囲を分けて整理する。
- GitHub CLI または GitHub app が使える場合は `Nkzono99/paper-harness-template` に構造化 Issue として起票する。
- 起票できない環境では、Issue 本文案を作成してユーザーに渡す。
