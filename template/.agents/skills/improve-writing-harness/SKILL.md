---
name: improve-writing-harness
description: Codex でプロジェクトローカルな執筆ハーネス摩擦を調査・修正する。
---

# improve-writing-harness

Codex で使う互換入口。実際の手順は `.claude/skills/improve-writing-harness/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- まず問題がプロジェクトローカルか、テンプレートに返すべき繰り返し摩擦かを切り分ける。
- テンプレートに返す価値がある場合は `raise-template-feedback` を使い、ローカル修正だけで閉じない。
- スクリプト、フック、ワークフローを変更したら該当する `make` ターゲットを実行する。
