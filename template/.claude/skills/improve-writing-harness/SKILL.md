---
name: improve-writing-harness
description: 執筆ハーネスのプロジェクトローカルな摩擦を特定し修正する。スクリプト、フック、ワークフローが繰り返し問題を起こす場合に使用。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# improve-writing-harness

リポジトリ構造、スクリプト、またはエージェントワークフローが論文執筆中に繰り返し摩擦を起こす場合にこのスキルを使用する。

## 目的

1. 摩擦を具体的に記述する。
2. 修正をこのリポジトリ内に留めるべきか、上流テンプレートにエスカレートすべきかを判断する。
3. プロジェクトローカルの修正の場合、ここで最小限の改善を実装する。
4. 再利用可能な修正の場合、`feedback-paper-harness` のための素材を準備する。

## 確認すべき入力

- `notes/writing-log.md`
- `notes/open-questions.md`
- `.claude/skills/`
- `scripts/`
- `.github/workflows/`
