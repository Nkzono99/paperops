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
- `archive-scratch` (`/archive-scratch`): 過去稿を sealed scratch archive として封印し、明示時だけ restart・一覧・確認・reset・restore を行う。

### 参照・関連研究

- `research-related-work`: 関連研究の調査設計、raw finding、採用文献を分ける。
- `source-reach-scan`: 外部 source channel と raw capture 方針を整理する。

### 主張・証拠

- `map-result-patterns`: raw result や figure data を evidence card へ束ねる。
- `scientific-gate`: 中心主張を Abstract / Conclusion / main figure に出してよいか、中心仮定や claim upgrade blocker も含めて判定する。
- `design-manuscript-claims`: 作業報告型の原稿を主張中心に再設計し、`paper_ir` の seed を作る。
- `design-paper-storyline`: 論文全体の story spine、Results hierarchy、Discussion functions を editorial architect 視点で固定し、Submission hygiene へ逃げる前に原稿内容の blocker を検出する。
- `plan-figure-story`: 本文生成前に中心 claim から visual obligation を作り、Figure 1、主図、補足図、missing figure を設計する。

### 原稿完成

- `finish-manuscript`: `/goal` で原稿を 1 から、または既存稿と feedback loop から投稿可能な状態まで進める route-level skill。詳細な gate、subagent、feedback routing、section compiler、final checks は下記の専門 skill へ委譲する。
- `audit-ai-draft`: AI 初稿をそのまま磨かず、claim / evidence / section compiler へ戻す routing skill として使う。
- `content-first-gate`: 原稿本文 blocker が残る間に Submission hygiene や harness 改修へ逸れないか確認する。
- `orchestrate-manuscript-subagents`: subagent roster、brief、privacy、subagent report、integration decision を管理する。
- `route-manuscript-feedback`: Issue Router と Backward propagation で feedback を evidence / story / section / prose / submission loop へ戻す。
- `compile-results-section`: `paper_ir` から Results の reader question、answer、quantitative evidence、figure、baseline/comparator rationale、consequence を作る。
- `compile-discussion-section`: `paper_ir` から Discussion functions、mechanism warrant、alternative、implication、decisive next test を作る。
- `compile-methods-section`: `paper_ir` から Methods の method unit、main text / supplement / code 配分、再実装情報を作る。
- `finalize-manuscript`: 完了宣言前に Finish criteria、review loop、mirror、引用、figure、AI disclosure、pre-submit を確認する。

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

- `resolve-local-paths`: `_paperops/refs/links.toml` と local path を確認する。`runops-main` の runops ディレクトリリンクを解決し、paper request queue や export bundle へ安全につなぐ入口でもある。
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

原稿編集では `make concept-term-check` と `_paperops/notes/views/concept-terms.md` も使う。AI 初稿で起きやすい concept-term compression、つまり強い英語名詞句への単語化は、claim / argument / evidence card の意味を本文へ写すときの語彙問題として扱い、必要なら普通の文へほどく。

Writer には card 正本や gate 語彙を直接読み込ませすぎない。`finish-manuscript` は薄い router として `content-first-gate`、`orchestrate-manuscript-subagents`、`route-manuscript-feedback`、`finalize-manuscript` を必要時に呼ぶ。story spine、Results hierarchy、Discussion functions、Methods definition registry は `design-paper-storyline` で固定し、`plan-figure-story` で visual obligation を本文生成前に固定する。その後、必要な card と controlled authoring view から `paper_ir` を作り、`compile-results-section`、`compile-discussion-section`、`compile-methods-section` を通してから本文生成へ進む。`section-contract-check` は Results hierarchy、Discussion functions、Methods definition registry の機能 block を確認する。`section-depth-check` は JA を `ja_chars`、EN を `en_words` で数え、length is floor, not target として one-paragraph subsections や短すぎる Results / Discussion を検出する。Submission hygiene は manuscript content が accepted になった後の最終面として扱う。

## 重要な境界

- 人間向けの高次構想は `story/` に置く。
- カード正本は `_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/`。
- `_paperops/notes/views/` には pure overview view と controlled authoring view がある。
- `_paperops/notes/views/concept-terms.md` は概念語ビューであり、claim / argument / evidence card の意味と本文語彙の対応を記録する。
- `_paperops/notes/views/*.md` は `view_type` と `source_of_truth` の front matter を持つ。`pure_overview` はカード総覧、`controlled_authoring` は本文語彙・条件名・読者順序の統制 view として扱う。
- `paper_ir` は生成一時物であり、手書き正本にはしない。
- `_paperops/defaults/contracts/` は文章テンプレートではなく paperops-managed の section 入出力契約である。論文固有差分は `_paperops/contracts/` overlay に置く。
- `_paperops/defaults/contracts/figures.yml` は figure story の標準契約であり、missing figure を本文生成前に見つけるための visual obligation を定義する。
- `_paperops/defaults/contracts/storyline.yml` は個別 section より上位の story 標準契約であり、reader_promise、evidence_ladder、Results hierarchy、Discussion functions を定義する。
- `manuscript/writing-profile.yml` は論文種別・投稿先ごとの overlay であり、`section_depth` の soft floor も置く。
- `_paperops/defaults/workflow/` は階層型状態機械、focus policy、subagent roster の標準規約である。`_paperops/workflow/` は現在状態、review loop、人間判断、任意の workflow overlay を置く。
- `_paperops/defaults/workflow/focus-policy.yml` と `check-content-first.py` は、本文 blocker 未解決のまま Submission hygiene や downstream harness だけへ逸れる作業を検出する。
- 作業用ドキュメントは原則日本語で書く。
- raw correspondence、未整理ファイル、個人環境の実パスは tracked file へ混ぜない。
- `_archives/` は sealed scratch archive。通常の skill は読まず、明示的な restore / inspect / compare 指示がある場合だけ扱う。
- `make skill-mirror-check` は `.agents/skills/` と `.claude/skills/` の対応を確認する。
