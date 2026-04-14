---
name: triage-template-feedback
description: 受信したテンプレートフィードバックを評価し、スコープ・ラベル・実装先を判断する。Issue トリアージ時に使用。
allowed-tools: Read, Glob, Grep
---

# triage-template-feedback

テンプレートフィードバックの Issue を評価する際、または問題がテンプレートリポジトリに属するかを判断する際にこのスキルを使用する。

## 目的

1. Issue 本文から問題を再現する。
2. 変更がテンプレートに属するか、プロジェクトローカルに留めるべきかを判断する。
3. `area:*`、`type:*`、`scope:*` ラベルで Issue を分類する。
4. 繰り返される摩擦を解消する最小の変更を提案する。

## 読み込むべき入力

- `README.md`
- `docs/architecture.md`
- `docs/change-policy.md`
- `docs/triage-rules.md`
- `template/` 配下の関連ファイル

## 出力形式

以下を含む簡潔なトリアージノートを作成する:

- 問題の説明
- 再現手順
- スコープの判断
- 提案する実装先
- 後方互換性の考慮事項
