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

下流スキャフォールドは `template/.agents/skills/` に共通の project skill 実体を提供し、Claude Code 用には `template/.claude/skills/` に同名の wrapper を提供する。Claude wrapper は `@${CLAUDE_SKILL_DIR}/../../../.agents/skills/<skill>/SKILL.md` で共通手順を読み込み、Claude 固有の `allowed-tools` / `argument-hint` だけを保持する:

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
- `open-paper-scan`
- `map-result-patterns`
- `review-public-manuscript`
- `start-manuscript-review`
- `collect-manuscript-review`
- `design-manuscript-claims`
- `audit-ai-draft`
- `contextualize-conditions`
- `calibrate-claims`
- `public-terminology-pass`
- `paragraph-surgery`
- `figure-story-audit`
- `venue-fit-review`
- `ai-disclosure-check`

状況別の入口:

- 初回セットアップ・上流更新: `setup`、`update-paperops`
- セッション再開・進捗記録: `resume-session`、`note-writing-session`
- 俯瞰・発散: `open-paper-scan`
- 執筆設計・本文調整: `design-manuscript-claims`、`calibrate-claims`、`paragraph-surgery`
- 結果パターン・AI 初稿の診断・条件文脈化: `map-result-patterns`、`audit-ai-draft`、`contextualize-conditions`
- 日英同期・公開語彙: `sync-ja-en`、`public-terminology-pass`
- 通読レビュー: `start-manuscript-review` で開始し、終了後に `collect-manuscript-review`
- 公開前点検: `review-public-manuscript`、`figure-story-audit`、`venue-fit-review`、`ai-disclosure-check`
- 外部 project link・上流改善: `resolve-local-paths`、`feedback-paper-harness`

レビュー系スキルの使い分け:

- `open-paper-scan`: 原稿、論文プロジェクト、執筆ハーネスを俯瞰し、まだ記録・実装・Issue 化に固定しない違和感、改善案、逆張り仮説を出す。
- `map-result-patterns`: raw result、figure data、analysis artifact を result pattern / evidence packet へ抽象化し、claim に昇格する前の中間層を作る。
- `review-public-manuscript`: section / weekly / pre-submit の粒度で公開原稿だけを読み、外部読者・一般研究者視点で未定義語、ローカル語、暗黙前提、再現性ギャップを検出する。
- `start-manuscript-review`: 人間が TeX/PDF を通読して直接編集するための review branch と inline comment ルールを準備する。
- `collect-manuscript-review`: TeX の直接編集 diff と `% REVIEW:` などの inline comment から `notes/reviews/review-YYYY-MM-DD.md` を生成し、必要に応じて source-of-truth 原稿と EN mirror に反映する。
- `design-manuscript-claims`: repo 内の brief / contribution claims / mirror status も読み、作業報告型の原稿を主張中心の構造へ再設計する。
- `audit-ai-draft`: AI 初稿を公開読者視点と repo 文脈の両方から診断し、論旨設計と改稿計画を作る。
- `contextualize-conditions`: 条件数、case count、run inventory を claim role と公開条件名へ翻訳する。
- `calibrate-claims`: evidence strength に合わせて防御的文体と過剰主張を調整する。
- `public-terminology-pass`: ローカル語・内部語・未定義略語を public terminology gate に沿って公開語へ置換する。
- `paragraph-surgery`: 段落単位で old-to-new flow、topic sentence、stress position を整える。
- `figure-story-audit`: figure/table が claim, evidence, boundary を支えているか監査する。
- `venue-fit-review`: 投稿先・読者モデルに照らして title、abstract、構成、必須要件を点検する。
- `ai-disclosure-check`: `notes/ai-use.md` と投稿先ポリシーに照らして AI 利用開示と人間検証を点検する。

`resolve-local-paths` は `refs/links.toml` を共有可能な external link registry、`refs/local/locations.toml` を untracked なローカル解決先として扱う。

セットアップとセッション記録のスキルは、`notes/result-pattern-map.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md` も公開・投稿前状態として扱う。

`.agents/skills/` は重複実装を避けるための source of truth であり、恒久的な手順変更は `.agents/skills/<skill>/SKILL.md` 側を更新する。`.claude/skills/` は cwd に依存しない `${CLAUDE_SKILL_DIR}` 参照を使う薄い互換入口に留める。`make skill-mirror-check` は同名 skill の存在と wrapper の source-of-truth 参照を機械的に確認する。

## CLI 配布

下流プロジェクトの作成と更新は `pops` CLI に統一する。標準実行は `uvx --from paper-harness-cli pops ...` である:

- `pops init`: `template/` 由来の bundled scaffold から新規論文プロジェクトを作成
- `pops doctor`: 初期化後のハーネス状態を診断
- `pops update-paperops`: 管理対象ハーネスファイルの更新計画を表示・適用
- `pops update-paperops --plan`: versioned upgrade chain を表示
- `pops links list/check`: paper draft の `refs/links.toml` と `refs/local` の対応を表示・検証
- `resolve-local-paths`: `kind = "runops_project"` の link では runops MCP の export / artifact / survey / paper request tool を優先し、追加要望は `runops.paper.request.draft` で検証してから handoff
- `pops feedback`: 上流へ戻す改善フィードバックの下書きを生成

`pull-template-updates` は旧名の互換入口であり、新規の更新導線では `update-paperops` を使う。
