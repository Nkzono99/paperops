---
name: triage-template-feedback
description: 受信したテンプレートフィードバックを評価し、スコープ・ラベル・実装先を判断する。Issue トリアージ時に使用。
allowed-tools: Read, Glob, Grep, Bash
---

# triage-template-feedback

テンプレートフィードバックの Issue を評価する際、または問題がテンプレートリポジトリに属するかを判断する際にこのスキルを使用する。

## 目的

1. `gh issue list --state open` でオープンな Issue を取得する。
2. 各 Issue の本文を `gh issue view <number>` で読み、問題を把握する。
3. 変更がテンプレートに属するか、プロジェクトローカルに留めるべきかを判断する。
4. `area:*`、`type:*`、`scope:*` ラベルで Issue を分類する。
5. 繰り返される摩擦を解消する最小の変更を提案する。

## 読み込むべき入力

- `README.md`
- `docs/architecture.md`
- `docs/change-policy.md`
- `docs/triage-rules.md`
- `template/` 配下の関連ファイル

## 出力形式

各 Issue について以下を含む簡潔なトリアージノートを作成する:

- Issue 番号とタイトル
- 問題の説明
- 再現手順
- スコープの判断
- 提案するラベル
- 提案する実装先
- 実施優先順位

## Issue とコミットの紐付け

トリアージ後に実装する際は、コミットメッセージに Issue 番号を含めて紐付ける:

```
fix: 問題の説明 (closes #123)
feat: 機能の説明 (closes #456)
design: 設計変更の説明 (closes #789, closes #790)
```

`closes #N` をコミットメッセージに含めることで、main にマージされた時点で自動的に Issue がクローズされる。

実装完了後に手動で Issue をクローズする場合は、対応コミットハッシュを参照するコメントを添えてクローズする:

```sh
gh issue close <number> --comment "<commit-hash> で対応済み。<変更内容の要約>"
```
