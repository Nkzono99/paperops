# スキルカタログ

## テンプレート保守

- `triage-template-feedback`: 受信した改善提案をスコープ判定する。
- `apply-template-improvement`: 承認済みのテンプレート改善を実装する。
- `review-template-regression`: テンプレート変更の安全性と下流互換性を確認する。
- `release`: version 更新、リリースノート、タグ、GitHub Release、PyPI workflow を処理する。

## 下流プロジェクト用スキル

共通実体は `template/.agents/skills/` に置く。`template/.claude/skills/` は Claude Code 用 wrapper で、共通手順を `.agents/skills/<skill>/SKILL.md` から読む。

### セットアップ

- `setup`: 初回セットアップ。
- `resume-session`: セッション再開。
- `note-writing-session`: 進捗記録。
- `update-paperops`: 上流 scaffold 更新。
- `pull-template-updates`: 旧名の互換入口。

### 参照・関連研究

- `resolve-local-paths`: `refs/links.toml` と local path を確認する。
- `update-refs`: 文献サマリーを整える。
- `source-reach-scan`: 外部 source channel と raw capture 方針を整理する。
- `research-related-work`: 関連研究の調査設計、raw finding、採用文献を分ける。

### 主張・証拠

- `map-result-patterns`: raw result や figure data を evidence card へ束ねる。
- `scientific-gate`: 中心主張を Abstract / Conclusion / main figure に出してよいか、中心仮定や claim upgrade blocker も含めて判定する。
- `design-manuscript-claims`: 作業報告型の原稿を主張中心に再設計する。
- `calibrate-claims`: evidence strength に合わせて主張の強さを調整する。
- `contextualize-conditions`: 条件数や run inventory を論文上の比較へ翻訳する。

### 原稿編集

- `import-manuscript`: 既存原稿を取り込む。
- `finish-manuscript`: `/goal` で原稿を 1 から、または既存稿と feedback loop から投稿可能な状態まで進める。
- `sync-ja-en`: 日英 block を同期する。
- `paragraph-surgery`: 段落単位で流れを整える。
- `polish-ai-draft`: claim lock 後に AI 初稿の文体を整える。
- `public-terminology-pass`: 内部語や未定義略語を公開語へ置換する。
- `audit-ai-draft`: AI 初稿を論旨設計へ戻して診断する。

### レビュー

- `review-public-manuscript`: 公開原稿だけを外部読者視点で読む。
- `peer-review-manuscript`: 投稿前原稿を査読者パネルとして読み、科学面、line-level readability、rendered figure を分けて見る。
- `respond-to-peer-review`: editor / reviewer comments を response matrix、closure audit、revision plan に分ける。
- `start-manuscript-review`: 人間の通読レビューを開始する。
- `collect-manuscript-review`: TeX diff と inline comment を回収する。
- `integrate-writing-feedback`: 人間レビューや自然文指示を feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。

### 投稿前点検

- `figure-story-audit`: figure/table が claim、decision boundary、path criterion、denominator、state visualization、本文参照を支えているか点検する。
- `venue-fit-review`: 投稿先・読者モデルとの fit を確認する。
- `ai-disclosure-check`: AI 利用開示と人間検証を確認する。

### ハーネス改善

- `open-paper-scan`: まだ記録や実装に固定しない俯瞰的な違和感を出す。
- `improve-writing-harness`: 論文プロジェクト内の執筆ハーネスを改善する。
- `feedback-paper-harness`: 再利用可能な摩擦を上流 `paperops` へ戻す。

## 重要な境界

- カード正本は `evidence/`、`claims/`、`review/`、`requests/`。
- `notes/views/` は俯瞰ビュー。旧 `notes/*.md` の一部は互換ビュー。
- 作業用ドキュメントは原則日本語で書く。
- raw correspondence、未整理ファイル、個人環境の実パスは tracked file へ混ぜない。
- `_archives/` は sealed scratch archive。通常の skill は読まず、明示的な restore / inspect / compare 指示がある場合だけ扱う。
- `make skill-mirror-check` は `.agents/skills/` と `.claude/skills/` の対応を確認する。
