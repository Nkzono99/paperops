# スキルカタログ

## テンプレート保守スキル

### `triage-template-feedback`

受信したフィードバックを読み取り、修正先を判断する:

- `template/` の構造
- ルートドキュメント
- 再利用可能ワークフロー
- テンプレート保守者向けスキル
- プロジェクトローカルのカスタマイズガイダンス

### `apply-template-improvement`

承認されたテンプレート改善を、下流の互換性を維持しつつ実装し、変更を文書化する。

### `review-template-regression`

提案されたテンプレート変更が、ミラー追跡、ノート継続性、refs 整理、安全性保護を弱めていないかチェックする。

## スキャフォールドに含まれるプロジェクトローカルスキル

下流スキャフォールドは `template/.claude/skills/` に以下のスキルを提供する:

- `setup`
- `resume-session`
- `sync-ja-en`
- `note-writing-session`
- `improve-writing-harness`
- `raise-template-feedback`
- `update-refs`
- `resolve-local-paths`
- `pull-template-updates`
- `import-manuscript`

## 配布自動化

リポジトリには公開ヘルパーも提供される:

- `scripts/publish-scaffold.sh`: `rsync` で `template/` を配布リポジトリに同期
