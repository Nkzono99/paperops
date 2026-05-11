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

下流スキャフォールドは `template/.claude/skills/` に実体となるスキルを提供し、Codex 用には `template/.agents/skills/` に同名の互換入口を提供する:

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
- `review-public-manuscript`
- `start-manuscript-review`
- `collect-manuscript-review`
- `design-manuscript-claims`

レビュー系スキルの使い分け:

- `review-public-manuscript`: 公開原稿だけを読み、外部読者・一般研究者視点で未定義語、ローカル語、暗黙前提、再現性ギャップを検出する。
- `start-manuscript-review`: 人間が TeX/PDF を通読して直接編集するための review branch と inline comment ルールを準備する。
- `collect-manuscript-review`: TeX の直接編集 diff と `% REVIEW:` などの inline comment から `notes/reviews/review-YYYY-MM-DD.md` を生成し、必要に応じて source-of-truth 原稿と EN mirror に反映する。
- `design-manuscript-claims`: repo 内の brief / contribution claims / mirror status も読み、作業報告型の原稿を主張中心の構造へ再設計する。

セットアップとセッション記録のスキルは、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md` も公開・投稿前状態として扱う。

`.agents/skills/` は重複実装を避けるための薄い入口であり、恒久的な手順変更は `.claude/skills/<skill>/SKILL.md` 側を source of truth として更新する。

## 配布自動化

リポジトリには公開ヘルパーも提供される:

- `scripts/publish-scaffold.sh`: `rsync` で `template/` を配布リポジトリに同期
