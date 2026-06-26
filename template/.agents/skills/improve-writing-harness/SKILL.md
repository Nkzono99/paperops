---
name: improve-writing-harness
description: 執筆ハーネスのプロジェクトローカルな摩擦を特定し修正する。スクリプト、フック、ワークフローが繰り返し問題を起こす場合に使用。
---

# improve-writing-harness

リポジトリ構造、スクリプト、またはエージェントワークフローが論文執筆中に繰り返し摩擦を起こす場合にこのスキルを使用する。

ユーザーが「俯瞰的に」「meta 的に」「まだ記録・実装しない」と頼んでいる場合、または改善対象がまだ曖昧な場合は、先に `/open-paper-scan` で発散的に眺める。この skill は、修正対象が project-local friction として切り出せた後に使う。

## 目的

1. 摩擦を具体的に記述する。
2. 修正をこのリポジトリ内に留めるべきか、上流テンプレートにエスカレートすべきかを判断する。
3. プロジェクトローカルの修正の場合、ここで最小限の改善を実装する。
4. 再利用可能な修正の場合、`feedback-paper-harness` のための素材を準備する。

## 確認すべき入力

- `_paperops/notes/writing-log.md`
- `_paperops/notes/open-questions.md`
- `.agents/skills/`
- `.claude/skills/`
- `scripts/`
- `.github/workflows/`

## Codex 実行メモ

- まず問題がプロジェクトローカルか、テンプレートに返すべき繰り返し摩擦かを切り分ける。
- テンプレートに返す価値がある場合は `feedback-paper-harness` を使い、ローカル修正だけで閉じない。
- スクリプト、フック、ワークフローを変更したら該当する `make` ターゲットを実行する。
