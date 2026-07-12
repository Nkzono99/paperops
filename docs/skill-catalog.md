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
- `design-paper-storyline`: 論文全体の story spine、project-owned の typed Results hierarchy、Discussion functions を editorial architect 視点で固定し、Submission hygiene へ逃げる前に原稿内容の blocker を検出する。
- `plan-figure-story`: 本文生成前に中心 claim から visual obligation を作り、Figure 1、主図、補足図、missing figure を設計する。

### 原稿完成

- `finish-manuscript`: `/goal` で原稿を 1 から、または既存稿と feedback loop から投稿可能な状態まで進める主入口。原稿内容は `develop-manuscript-content`、投稿メタデータや submission candidate は `submission-gate` へ分ける。
- `develop-manuscript-content`: claims、storyline、figure story、Results hierarchy、Discussion functions、Methods definition、section compiler、block flow、本文 prose を進める原稿内容専用入口。ORCID、affiliation、license などの投稿メタデータは扱わない。
- `audit-ai-draft`: AI 初稿をそのまま磨かず、claim / evidence / section compiler へ戻す routing skill として使う。AI Writer の authoring intent が本文 prose に漏れた場合もここで検出し、`% INTENT:` / `% TODO-PAPER:`、notes、requests へ戻す。
- `route-manuscript-feedback`: Issue Router と Backward propagation で feedback を evidence / story / section / prose / submission loop へ戻す。
- `submission-gate`: `manuscript/` の authoring source と `submission/` の submission candidate / round snapshot を分け、revision-authoring 後の再投稿も含めて投稿版に予測稿、open AREQ、`xx`、AI intent が残らないか確認する。

### 原稿完成の内部 route

通常は `/finish-manuscript` から呼ばせる。特定の blocker を人間が明示した場合だけ直接使う。

- `content-first-gate`: 原稿本文 blocker が残る間に Submission hygiene や harness 改修へ逸れないか確認する。原稿内容を進める場合は `develop-manuscript-content` へ渡す。
- `orchestrate-manuscript-subagents`: subagent roster、brief、privacy、subagent report、integration decision を管理する。
- `compile-results-section`: `_paperops/model/editorial/results-hierarchy.yml` の `RHI-*` ID と `next_item_id` chain を検査し、`paper_ir` から Results の reader question、answer、quantitative evidence、figure、baseline/comparator rationale、consequence を作る。
- `compile-discussion-section`: `paper_ir` から Discussion functions、mechanism warrant、alternative、implication、decisive next test を作る。
- `compile-methods-section`: `paper_ir` から Methods の method unit、main text / supplement / code 配分、再実装情報を作る。
- `draft-predicted-results`: goal 中に追加シミュレーションで閉じられる Results / Discussion blocker を、未検証予測稿と analysis request として扱う。
- `review-block-flow`: DRAFTED section の block flow、author stance、reader question を読み直し、block operation table で move / split / merge / delete / add を決める。
- `finalize-manuscript`: 完了宣言前に Finish criteria、review loop、mirror、引用、figure、AI disclosure、pre-submit を確認する。

### レビュー・査読

- `integrate-writing-feedback`: 人間レビューや自然文指示を feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
- `peer-review-manuscript`: 投稿前原稿を査読者パネルとして読み、科学面、line-level readability、rendered figure を分けて見る。
- `respond-to-peer-review`: editor / reviewer comments を response matrix、closure audit、revision plan に分ける。
- `review-public-manuscript`: 公開原稿だけを外部読者視点で読み、AI authoring intent leak も読者に見える meta prose として検出する。

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
- `polish-ai-draft`: claim lock 後に AI 初稿の文体を整える。作業計画や判断保留を自然な本文に見せかけず、reader-facing 内容か `% INTENT:` / `% TODO-PAPER:` / request かに分ける。

### 図表・投稿前点検

- `design-paper-figure`: `plan-figure-story` または figure blocker から呼ぶ。個別図について「データがあるから図にする」状態を避け、reader task と runops handoff まで含む Figure design brief を作る。
- `figure-story-audit`: `plan-figure-story` 後、または投稿前の figure blocker で呼ぶ。figure/table が claim、decision boundary、denominator、本文参照を支えているか点検する。
- `venue-fit-review`: 投稿先・読者モデルとの fit を確認する。
- `ai-disclosure-check`: AI 利用開示と人間検証を確認する。
- `submission-gate`: 投稿・外部共有・再投稿前の strict gate と round snapshot 記録を扱う。
- `sync-ja-en`: 日英 block を同期する。

### レビュー補助

- `start-manuscript-review`: 人間の通読レビューを開始する。
- `collect-manuscript-review`: TeX diff と inline comment を回収する。`% INTENT:` は AI Writer が本文に混ぜそうになった authoring intent の退避先として扱う。

## paper_ir と section compiler

原稿編集では `make concept-term-check` と `_paperops/notes/views/concept-terms.md` も使う。AI 初稿で起きやすい concept-term compression、つまり強い英語名詞句への単語化は、claim / argument / evidence card の意味を本文へ写すときの語彙問題として扱い、必要なら普通の文へほどく。

Writer には card 正本や gate 語彙を直接読み込ませすぎない。`finish-manuscript` は薄い router として `develop-manuscript-content`、`content-first-gate`、`orchestrate-manuscript-subagents`、`route-manuscript-feedback`、`finalize-manuscript`、`submission-gate` を必要時に呼ぶ。`develop-manuscript-content` は原稿内容だけを扱い、ORCID、affiliation、license などの投稿メタデータは `submission-gate` へ残す。story spine、typed Results hierarchy、Discussion functions、Methods definition registry は `design-paper-storyline` で固定し、`plan-figure-story` で visual obligation を本文生成前に固定する。Results の値は `_paperops/model/editorial/results-hierarchy.yml` に置き、storyline view へ複製しない。個別図は `design-paper-figure` で図の設計意図、reader task、takeaway、encoding、denominator、uncertainty、caption、runops handoff を Figure design brief にしてから `figure-story-audit` へ回す。未実行の追加シミュレーションが投稿前に現実的で、予測根拠を持つ場合は `draft-predicted-results` で `PREDICTED-RESULT` / `SIM-REQUEST` comment、`xx` 置換条件、`_paperops/model/issues/analysis/` を接続し、Future Work や defensive prose に逃がさない。`manuscript/` は living authoring source として予測稿を管理できるが、submission candidate / round snapshot には残さない。その後、必要な card と controlled authoring view から `paper_ir` を作り、`compile-results-section`、`compile-discussion-section`、`compile-methods-section` を通してから本文生成へ進む。DRAFTED から AUDITED へ進む前に `review-block-flow` で block operation table を作り、author stance、reader question、why here、move / split / merge / delete / add を明示する。AI Writer の authoring intent、TODO、後で埋める内容、作業計画は公開 prose にせず `% INTENT:` / `% TODO-PAPER:`、`_paperops/notes/`、`_paperops/model/issues/` へ置く。`authoring-intent-check` は audit では advisory、finish / pre-submit では strict に使う。`section-contract-check` は `RHI-*` ID、`next_item_id` chain、Discussion functions、Methods definition registry を確認する。既存下流 project は M0-0003 採用まで legacy Markdown fallback を利用できる。`section-depth-check` は JA を `ja_chars`、EN を `en_words` で数え、length is floor, not target として one-paragraph subsections や短すぎる Results / Discussion を検出する。`card-coverage-check` は原稿中の図、citation、block ID が card 層へ接続されているかを advisory に見る。`check-predicted-results.py` は audit では advisory、finish / submission gate / pre-submit では strict に使う。Submission hygiene は manuscript content が accepted になった後の最終面として扱う。

## 重要な境界

PaperOps 2 P1-Bではmanaged registry / JSON Schema / checkerとproject-ownedのResearch / Editorial / Results hierarchy / Manuscript / Issue / Publication stateを分離する。P2 migration、P3 compiler / Writer、P4 workflowでは、定型的なinventory、hash、shadow、adopt、compile、scope、conservation、impact、apply、recovery、rollbackを`pops model` / `pops compile` / `pops write` / `pops workflow`へ渡し、skillやAI Agentにshell手順を再実装させない。AIは全原稿candidateを読み、scientific / editorial judgment、候補の意味、棄却理由、global replanを扱うが、六モデルへ架空値を補わずscopeを黙って広げない。P7の新規projectはdefault v2だが、既存projectのauthority、legacy artifact、living TeX直接編集は維持する。

`make schema-check` は schema → references → semantics → canonical semantic-v1 hash の順で検査し、mechanism-led、boundary-led、negative-result-led の三つの合成fixtureを回帰corpusとする。

- 人間向けの高次構想は `story/` に置く。
- カード正本は `_paperops/model/research/`、`_paperops/model/research/`、`_paperops/model/issues/`、`_paperops/model/issues/`。
- source summary は背景だけなら hold に留め、claim_boundary、parameter_choice、reviewer_objection、method_precedent に使う場合だけ source card に昇格する。
- `_paperops/notes/views/` には pure overview view と controlled authoring view がある。
- `_paperops/notes/views/concept-terms.md` は概念語ビューであり、claim / argument / evidence card の意味と本文語彙の対応を記録する。
- `_paperops/notes/views/*.md` は `view_type` と `source_of_truth` の front matter を持つ。`pure_overview` はカード総覧、`controlled_authoring` は本文語彙・条件名・読者順序の統制 view として扱う。
- `paper_ir` は生成一時物であり、手書き正本にはしない。
- `_paperops/defaults/contracts/` は文章テンプレートではなく paperops-managed の section 入出力契約である。論文固有差分は `_paperops/contracts/` overlay に置く。
- `_paperops/defaults/schemas/*` は paperops-managed schema default、`_paperops/model/editorial/results-hierarchy.yml` は project-owned typed state である。
- `_paperops/defaults/contracts/figures.yml` は figure story の標準契約であり、missing figure を本文生成前に見つけるための visual obligation を定義する。
- `_paperops/defaults/contracts/storyline.yml` は個別 section より上位の story 標準契約であり、reader_promise、evidence_ladder、Results hierarchy、Discussion functions を定義する。
- `manuscript/writing-profile.yml` は論文種別・投稿先ごとの overlay であり、`section_depth` の soft floor も置く。
- `_paperops/defaults/workflow/` は階層型状態機械、focus policy、subagent roster の標準規約である。`_paperops/workflow/` は現在状態、review loop、人間判断、任意の workflow overlay を置く。
- `_paperops/defaults/workflow/focus-policy.yml` と `check-content-first.py` は、本文 blocker 未解決のまま Submission hygiene や downstream harness だけへ逸れる作業を検出する。
- 作業用ドキュメントは原則日本語で書く。
- raw correspondence、未整理ファイル、個人環境の実パスは tracked file へ混ぜない。
- `_archives/` は sealed scratch archive。通常の skill は読まず、明示的な restore / inspect / compare 指示がある場合だけ扱う。
- `make skill-mirror-check` は `.agents/skills/` と `.claude/skills/` の対応を確認する。
