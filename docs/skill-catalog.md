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

### `release`

`paperops` のリリースノート作成、version 更新、検証、タグ作成、GitHub Release 公開、PyPI publish workflow 確認までを行う。

## スキャフォールドに含まれるプロジェクトローカルスキル

下流スキャフォールドは `template/.claude/skills/` に実体となるスキルを提供し、Codex 用には `template/.agents/skills/` に同名の互換入口を提供する:

- `setup`
- `resume-session`
- `sync-ja-en`
- `note-writing-session`
- `improve-writing-harness`
- `feedback-paper-harness`
- `update-refs`
- `resolve-local-paths`
- `update-paperops`
- `pull-template-updates`
- `import-manuscript`
- `review-public-manuscript`
- `start-manuscript-review`
- `collect-manuscript-review`
- `design-manuscript-claims`
- `calibrate-claims`
- `public-terminology-pass`
- `paragraph-surgery`
- `figure-story-audit`
- `venue-fit-review`
- `ai-disclosure-check`

レビュー系スキルの使い分け:

- `review-public-manuscript`: section / weekly / pre-submit の粒度で公開原稿だけを読み、外部読者・一般研究者視点で未定義語、ローカル語、暗黙前提、再現性ギャップを検出する。
- `start-manuscript-review`: 人間が TeX/PDF を通読して直接編集するための review branch と inline comment ルールを準備する。
- `collect-manuscript-review`: TeX の直接編集 diff と `% REVIEW:` などの inline comment から `notes/reviews/review-YYYY-MM-DD.md` を生成し、必要に応じて source-of-truth 原稿と EN mirror に反映する。
- `design-manuscript-claims`: repo 内の brief / contribution claims / mirror status も読み、作業報告型の原稿を主張中心の構造へ再設計する。
- `calibrate-claims`: evidence strength に合わせて防御的文体と過剰主張を調整する。
- `public-terminology-pass`: ローカル語・内部語・未定義略語を public terminology gate に沿って公開語へ置換する。
- `paragraph-surgery`: 段落単位で old-to-new flow、topic sentence、stress position を整える。
- `figure-story-audit`: figure/table が claim, evidence, boundary を支えているか監査する。
- `venue-fit-review`: 投稿先・読者モデルに照らして title、abstract、構成、必須要件を点検する。
- `ai-disclosure-check`: `notes/ai-use.md` と投稿先ポリシーに照らして AI 利用開示と人間検証を点検する。

セットアップとセッション記録のスキルは、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md` も公開・投稿前状態として扱う。

`.agents/skills/` は重複実装を避けるための薄い入口であり、恒久的な手順変更は `.claude/skills/<skill>/SKILL.md` 側を source of truth として更新する。`make skill-mirror-check` は同名 skill の存在と source-of-truth 参照を機械的に確認する。

## CLI 配布

下流プロジェクトの作成と更新は `pops` CLI に統一する。標準実行は `uvx --from paper-harness-cli pops ...` である:

- `pops init`: `template/` 由来の bundled scaffold から新規論文プロジェクトを作成
- `pops doctor`: 初期化後のハーネス状態を診断
- `pops update-paperops`: 管理対象ハーネスファイルの更新計画を表示・適用
- `pops update-paperops --plan`: versioned upgrade chain を表示
- `pops links list/check`: paper draft の `refs/links.toml` と `refs/local` の対応を表示・検証
- `pops feedback`: 上流へ戻す改善フィードバックの下書きを生成

`pull-template-updates` は旧名の互換入口であり、新規の更新導線では `update-paperops` を使う。
