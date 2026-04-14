# 変更履歴

## 0.2.0 - 2026-04-14

- 全ドキュメント・スキル・ルール・スクリプトのユーザー向けテキストを日本語化
- protect-files フックを廃止し、settings.json の deny パターン + rules/ による保護に移行
- validate-mirror フックを廃止（`make mirror-check` で手動実行に変更）
- SessionStart フックを廃止（`/resume-session` スキルに統合）
- `pull-template-updates` スキルを追加（上流テンプレート変更の下流取り込み）
- AGENTS.md を CLAUDE.md と同一内容に統一

## 0.1.0 - 2026-04-13

- `paper-template` リポジトリ構造を初期化
- ビルド、ミラー検証、リリースパッケージング用の再利用可能 GitHub ワークフローを追加
- Issue フォームとテンプレート保守スキルを追加
- `template/` 配下に下流論文スキャフォールド一式を追加
