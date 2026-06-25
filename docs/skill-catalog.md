# スキルカタログ

## テンプレート保守

- `triage-template-feedback`: 受信した改善提案をスコープ判定する。
- `apply-template-improvement`: 承認済みのテンプレート改善を実装する。
- `review-template-regression`: テンプレート変更の安全性と下流互換性を確認する。
- `release`: version 更新、リリースノート、タグ、GitHub Release、PyPI workflow を処理する。

## 下流プロジェクト用スキル

共通実体は `template/.agents/skills/` に置く。`template/.claude/skills/` は Claude Code 用 wrapper で、共通手順を `.agents/skills/<skill>/SKILL.md` から読む。

downstream skill は route-level skills と leaf skills に分ける。

- Route-level skills は `/goal`、大きな workflow、状態遷移の入口として使う。読み始める範囲は広くなりやすいため、常時読むものと必要時に読むものを分ける。
- Leaf skills は狭い点検や局所作業に使う。詳細な checklist は leaf 側へ寄せ、route skill は「いつ呼ぶか」を短く書く。

## Route-level skills

### セットアップ・再開

- `setup`: 初回セットアップ。
- `resume-session`: セッション再開。
- `import-manuscript`: 既存原稿を取り込む。
- `update-paperops`: 上流 scaffold 更新。
- `pull-template-updates`: 旧名の互換入口。将来は短い redirect のみにする。

### 参照・関連研究

- `research-related-work`: 関連研究の調査設計、raw finding、採用文献を分ける。
- `source-reach-scan`: 外部 source channel と raw capture 方針を整理する。

### 主張・証拠

- `map-result-patterns`: raw result や figure data を evidence card へ束ねる。
- `scientific-gate`: 中心主張を Abstract / Conclusion / main figure に出してよいか、中心仮定や claim upgrade blocker も含めて判定する。
- `design-manuscript-claims`: 作業報告型の原稿を主張中心に再設計し、`paper_ir` の seed を作る。

### 原稿完成

- `finish-manuscript`: `/goal` で原稿を 1 から、または既存稿と feedback loop から投稿可能な状態まで進める。Writer の前に `paper_ir` と section compiler を通す。
- `audit-ai-draft`: AI 初稿をそのまま磨かず、claim / evidence / section compiler へ戻す routing skill として使う。

### レビュー・査読

- `integrate-writing-feedback`: 人間レビューや自然文指示を feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
- `peer-review-manuscript`: 投稿前原稿を査読者パネルとして読み、科学面、line-level readability、rendered figure を分けて見る。
- `respond-to-peer-review`: editor / reviewer comments を response matrix、closure audit、revision plan に分ける。
- `review-public-manuscript`: 公開原稿だけを外部読者視点で読む。

### 俯瞰・改善

- `open-paper-scan`: まだ記録や実装に固定しない俯瞰的な違和感を出す。
- `improve-writing-harness`: 論文プロジェクト内の執筆ハーネスを改善する。
- `feedback-paper-harness`: 再利用可能な摩擦を上流 `paperops` へ戻す。

## Leaf skills

### 参照・ローカル状態

- `resolve-local-paths`: `refs/links.toml` と local path を確認する。
- `update-refs`: 文献サマリーを整える。
- `note-writing-session`: 進捗記録。

### 主張・条件・語彙

- `calibrate-claims`: evidence strength に合わせて主張の強さを調整する。
- `contextualize-conditions`: 条件数や run inventory を論文上の比較へ翻訳する。
- `public-terminology-pass`: 内部語や未定義略語を公開語へ置換する。
- `paragraph-surgery`: 段落単位で流れを整える。
- `polish-ai-draft`: claim lock 後に AI 初稿の文体を整える。

### 図表・投稿前点検

- `figure-story-audit`: figure/table が claim、decision boundary、denominator、本文参照を支えているか点検する。
- `venue-fit-review`: 投稿先・読者モデルとの fit を確認する。
- `ai-disclosure-check`: AI 利用開示と人間検証を確認する。
- `sync-ja-en`: 日英 block を同期する。

### レビュー補助

- `start-manuscript-review`: 人間の通読レビューを開始する。
- `collect-manuscript-review`: TeX diff と inline comment を回収する。

## paper_ir と section compiler

原稿編集では `make concept-term-check` と `notes/views/concept-terms.md` も使う。AI 初稿で起きやすい concept-term compression、つまり強い英語名詞句への単語化は、claim / argument / evidence card の意味を本文へ写すときの語彙問題として扱い、必要なら普通の文へほどく。

Writer には card 正本や gate 語彙を直接読み込ませすぎない。`finish-manuscript` は、必要な card と controlled authoring view から `paper_ir` を作り、`compile-results`、`compile-discussion`、`compile-methods` の section compiler を通してから本文生成へ進む。

## 重要な境界

- カード正本は `evidence/`、`claims/`、`review/`、`requests/`。
- `notes/views/` には pure overview view と controlled authoring view がある。
- `notes/views/concept-terms.md` は概念語ビューであり、claim / argument / evidence card の意味と本文語彙の対応を記録する。
- `paper_ir` は生成一時物であり、手書き正本にはしない。
- 作業用ドキュメントは原則日本語で書く。
- raw correspondence、未整理ファイル、個人環境の実パスは tracked file へ混ぜない。
- `_archives/` は sealed scratch archive。通常の skill は読まず、明示的な restore / inspect / compare 指示がある場合だけ扱う。
- `make skill-mirror-check` は `.agents/skills/` と `.claude/skills/` の対応を確認する。
