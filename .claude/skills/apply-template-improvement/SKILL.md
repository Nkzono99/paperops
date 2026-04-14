---
name: apply-template-improvement
description: 承認されたテンプレート改善を、後方互換性とドキュメント更新を伴って安全に実装する。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# apply-template-improvement

テンプレートの変更が承認され、安全に実装する必要がある場合にこのスキルを使用する。

## 目的

1. ルートと `template/` のファイルを最小限のセットで更新する。
2. マイグレーションが明示的に意図されていない限り、既存の下流の期待を維持する。
3. 実装と並行してドキュメントと変更履歴のエントリを更新する。
4. 変更後にローカル smoke チェックを実行する。

## チェックリスト

- 編集前に影響を受けるディレクトリとスクリプトを確認する。
- ユーザーに影響する変更は `CHANGELOG.md` を更新する。
- `docs/` の関連ドキュメントを調整する。
- `make smoke` を実行する。
- 下流リポジトリに残るマイグレーション作業を要約する。

## Issue とコミットの紐付け

コミットメッセージに対応 Issue 番号を含めること:

```
fix: 問題の説明 (closes #123)
feat: 機能の説明 (closes #456)
design: 設計変更の説明 (closes #789)
```

複数の Issue を一つのコミットで解決する場合は、すべての番号を列挙する:

```
design: 構造変更の説明 (closes #4, closes #5)
```

実装完了後に手動で Issue をクローズする場合:

```sh
gh issue close <number> --comment "<commit-hash> で対応済み。<変更内容の要約>"
```
