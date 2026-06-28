# アーキテクチャ

`paperops` は、テンプレート保守と個別論文執筆を分ける。目的は、AI に原稿を直接書かせることではなく、研究状態を検証可能な中間層へ整理し、承認済みの材料だけを論文本文へ変換することである。

今回の基本方針は、人間が普段見る面と AI が執筆に使う内部状態を分けることである。人間側は `story/`、`manuscript/`、`submission/`、レビューコメントを主な接点にする。AI/ハーネス側の evidence、claims、refs、requests、workflow、contracts、notes/views は `_paperops/` に寄せ、必要な skill と CLI が読みに行く。

## ルート層

リポジトリルートは、下流論文リポジトリへ配るものを管理する。

- `template/`: bundled scaffold の source of truth
- `src/paperops/`: `pops` CLI
- `.github/workflows/`: reusable workflow
- `.github/ISSUE_TEMPLATE/`: テンプレート改善の受け口
- `.agents/skills/`, `.claude/skills/`: テンプレート保守 skill
- `docs/`, `CHANGELOG.md`: 変更方針と配布記録

この層の役割は、ハーネスを安全に進化させることである。

## 下流論文層

`template/` は個別論文リポジトリに展開される。主な層は次の通り。

- `story/`: 人間が読む構想、story seed、ストーリーラインの入口
- `AGENTS.project.md`, `CLAUDE.project.md`: project-owned の恒久指示
- `Makefile.project`: project-owned の tracked Make target
- `manuscript/`: 日英原稿、ミラー制御、投稿先情報
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX
- `_paperops/`: AI とハーネスが使う内部状態
- `_handoff/`: 人間から AI へ渡す未整理ファイル
- `_archives/`: 過去稿を sealed split bundle として封印する scratch archive

`_paperops/` の内部は次のように分ける。

- `_paperops/defaults/contracts/`: paperops-managed の Storyline と Introduction / Methods / Results / Discussion / Conclusion / Figure story 標準契約
- `_paperops/defaults/workflow/`: paperops-managed の状態機械、focus policy、subagent roster
- `_paperops/contracts/`: 論文固有の contract overlay
- `_paperops/workflow/`: 現在状態、review round summary、人間判断、任意の workflow overlay
- `_paperops/refs/`: 文献サマリー、関連研究調査、外部 source、外部 project link、外部 bundle import state
- `_paperops/evidence/`: result / figure / source card
- `_paperops/claims/`: claim / scientific gate / argument card
- `_paperops/review/`: feedback / review round / response card
- `_paperops/requests/`: analysis / writing request card
- `_paperops/notes/`: AI 利用、再現性、handoff、decision log、controlled authoring view

旧 top-level の `contracts/`、`workflow/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` は互換期間中は scripts / CLI が読むが、新規 scaffold の正道は `_paperops/` である。

## 層契約

| 層 | 役割 | 正本性 | 主な更新入口 |
| --- | --- | --- | --- |
| `story/` | 人間が読む高次ストーリー、仮説、期待する evidence path、結果に応じた分岐 | 人間向け構想 | `/design-paper-storyline`, prompt での相談 |
| `AGENTS.project.md`, `CLAUDE.project.md` | managed core を編集せず project 固有の恒久指示を置く | project overlay | 人間または Agent の明示更新 |
| `Makefile.project` | project 固有の tracked target を置く | project overlay | 人間または Agent の明示更新 |
| `_paperops/evidence/` | result / figure / source を論文上の証拠単位へ整理する | AI 内部正本 | `/map-result-patterns`, `/research-related-work`, `/design-paper-figure` |
| `_paperops/claims/` | claim、scientific gate、argument を管理する | AI 内部正本 | `/scientific-gate`, `/design-manuscript-claims` |
| `_paperops/review/` | 人間レビュー、模擬査読、実査読 response を管理する | AI 内部正本 | `/integrate-writing-feedback`, `/peer-review-manuscript`, `/respond-to-peer-review` |
| `_paperops/requests/` | 追加解析や改稿依頼を管理する | AI 内部正本 | `/integrate-writing-feedback`, runops handoff |
| `_paperops/notes/views/` の pure overview view | 正本カードを俯瞰する | 派生 view | 該当 card 更新後に手動または半自動で更新 |
| `_paperops/notes/views/` の controlled authoring view | 本文での呼び方、条件名、概念語、読者向け語彙、story spine を統制する | 編集可能な統制 view | `/design-paper-storyline`, `/public-terminology-pass`, `/contextualize-conditions`, `/polish-ai-draft` |
| `paper_ir` | card / view から Writer に渡す材料を section ごとにまとめる | 生成一時物 | `compile-results-section` / `compile-discussion-section` / `compile-methods-section` |
| `_paperops/defaults/contracts/` | story spine、section ごとの読者質問、入力、出力、禁止構造と figure story の標準契約を定める | managed default | `design-paper-storyline` / section compiler / `plan-figure-story` / audit-section |
| `_paperops/contracts/` | 標準契約から外れる論文固有の差分だけを同名 file で置く | project overlay | 人間または Agent の明示更新 |
| `manuscript/writing-profile.yml` | 論文種別、投稿先、分野別要求を section 契約へ重ねる | プロジェクト設定 | 初期 setup、投稿先変更時 |
| `_paperops/defaults/workflow/` | 状態機械、content-first focus policy、subagent role roster の標準規約を管理する | managed default | `pops workflow`, `content-first-gate`, `route-manuscript-feedback`, `orchestrate-manuscript-subagents` |
| `_paperops/workflow/` | 現在状態、section 状態、review loop、stale 伝播、人間判断、任意の workflow overlay を管理する | project state | `pops workflow`, review loop |
| `.paperops/cache/` | section plan や一時 IR を置く | Git 管理しない生成物 | section compiler |
| `manuscript/` | living manuscript / authoring source。投稿後や査読後も編集してよい本文 source | 編集中の成果物 | Writer / editor pass / revision-authoring |
| `submission/` | 投稿先に合わせた submission candidate と提出済み round snapshot | 派生成果物・証跡 | `submission-gate` と投稿前作業 |
| `_handoff/` | 未整理入力の一時置き場 | Git 管理しない | 人間入力、raw file intake |
| `_archives/` | sealed scratch archive | 通常読まない封印物 | `pops scratch archive/restart/restore` |

`_paperops/notes/views/storyline.md`、`_paperops/notes/views/concept-terms.md`、`_paperops/notes/views/condition-context-map.md` は controlled authoring view として扱う。ここには「カード正本から見える意味」を、本文の story spine、語彙、条件名へ変換するときの判断を書く。

`_paperops/notes/views/concept-terms.md` は概念語ビューである。claim / argument / evidence card の意味を強い英語名詞句へ圧縮しすぎていないかを確認し、accepted term、普通の文へほどく語、avoid 語を分ける。`concept-term-check` はこの concept-term compression を検出し、必要なら結果の層へほどくよう促す。

## C 案のストーリー状態

原稿を書く前の story 設計は一段ではなく、次の三層に分ける。

1. `story/` の story seed: 研究質問、初期メカニズム仮説、期待する evidence path、結果が外れた場合の分岐を書く。
2. `_paperops/notes/views/storyline.md`、`_paperops/defaults/contracts/storyline.yml`、必要な `_paperops/contracts/storyline.yml` overlay: story seed を Results hierarchy、Discussion functions、section 契約へ落とす中間言語にする。
3. `manuscript/`: 実際の結果、図、解析、レビューを反映した読者向け本文を書く。

workflow は C 案として `SCOPED -> STORY_SEEDED -> EVIDENCE_PLANNED -> EVIDENCE_READY -> STORY_RECONCILED -> ARCHITECTURE_LOCKED -> SECTION_PLANNED -> ...` を採用する。

- `STORY_SEEDED`: まだ証拠は揃っていなくても、何を明らかにしたいか、どんなメカニズムを想定するかを人間が確認した状態。
- `EVIDENCE_PLANNED`: 必要な simulation、analysis、figure、比較軸、仮説が外れた場合の改稿条件を列挙した状態。
- `EVIDENCE_READY`: 実際の evidence card と figure card が揃った状態。
- `STORY_RECONCILED`: story seed と実結果を照合し、主張範囲、negative / boundary story、修正後の論旨を人間が確認した状態。
- `ARCHITECTURE_LOCKED`: section 契約、storyline、figure story が本文生成に入れる程度に固定された状態。

この設計では、たとえば「プラズマによる月面ダストの静電的離脱可能性」のような論文で、最初に「どのように帯電し、どの機構で、どれくらい離脱可能性が妥当か」を `story/` に置ける。その後、表面帯電 3D 図、帯電強度と機構、クーロン力の時系列、離脱経路での仕事や速度、粒径や配置依存性を evidence plan にし、結果が仮説と合えば story を強め、外れれば `STORY_RECONCILED` で論旨を作り直す。

## 情報フロー

1. 人間は主に prompt、`story/`、原稿レビュー、自然文の判断を出す。
2. Agent は必要に応じて `_paperops/review/`、`_paperops/evidence/`、`_paperops/claims/`、`_paperops/requests/` を更新する。
3. Abstract、Conclusion、主要図表に使う claim は `_paperops/claims/gates/` で readiness を確認する。
4. 本文に出る強い名詞句は `_paperops/notes/views/concept-terms.md` で確認し、accepted term、普通の文へほどく語、avoid 語を分ける。
5. `pops workflow status` と `pops workflow next` で、全体状態、stale section、次に通す guard を確認する。
6. `content-first-gate`、`_paperops/defaults/workflow/focus-policy.yml`、`make content-first-check` で、次の作業が本文 blocker を減らす intent かを確認する。
7. subagent を使う場合は `orchestrate-manuscript-subagents` で `_paperops/defaults/workflow/subagent-roster.yml` と必要な project overlay を読み、main agent / orchestrator が role brief、privacy、`subagent_report`、integration decision を管理する。
8. `_paperops/defaults/contracts/<section>.yml`、必要な `_paperops/contracts/<section>.yml` overlay、`manuscript/writing-profile.yml` を重ねて、section が答える読者質問、必要出力、`section_depth` floor を確認する。
9. 本文生成前に `design-paper-storyline` で story spine、Results hierarchy、Discussion functions、Methods definition registry を固定する。
10. 本文生成前に `plan-figure-story` で中心 claim から visual obligation を作り、state/setup 図、criterion 図、primary evidence 図、mechanism/boundary 図の欠落を確認する。
11. 原稿を書く前に、必要な範囲で `paper_ir` と section plan を作る。生成物は `.paperops/cache/` に置き、Git 管理しない。
12. section compiler が Methods / Results / Discussion それぞれの reader question、answer、evidence、figure、caveat location、sentence budget を決める。
13. Writer は `paper_ir` と承認済み claim package を使って本文を書く。Writer に生の card ontology を直接渡しすぎない。
14. Review 後は `route-manuscript-feedback` と `pops workflow route-review` で evidence / story / section / prose / submission loop のどこへ戻るかを決め、上流 artifact が変わったら `pops workflow invalidate <artifact-id>` で依存 section を stale にする。
15. 原稿修正は最後に行う。本文だけ直して上流の claim や evidence を放置しない。
16. Submission hygiene は STRUCTURE_ACCEPTED 後に扱う。著者 metadata、license、Open Research DOI、readiness-check 改修は、Results hierarchy や Discussion functions の blocker より優先しない。投稿・外部共有・再投稿の直前だけ `submission-gate` で submission candidate を strict に確認し、提出済み round snapshot は `_paperops/workflow/submission-ledger.yml` に記録する。

## paper_ir と section compiler

`paper_ir` は、既存 card と controlled authoring view から作る生成一時物である。新しい手書き正本にはしない。目的は、研究 integrity 層と文章層の間に、読者向けの変換契約を置くことである。

`_paperops/defaults/contracts/` は文章テンプレートではなく、storyline と section ごとの入出力契約である。`_paperops/defaults/contracts/storyline.yml` は reader_promise、central_claim、evidence_ladder、Results hierarchy、Discussion functions を個別 section より上位で固定する。論文固有に変える場合だけ `_paperops/contracts/` に同名 overlay を置く。Introduction は `problem -> unresolved tension -> precise gap -> approach -> contribution -> scope` のような論理機能を持ち、Methods / Results / Discussion はそれぞれ情報配置、subsection 契約、推論型を明示する。`manuscript/writing-profile.yml` は `paper_type: computational_modeling` のような論文種別 overlay と投稿先要求を重ねる。

`_paperops/defaults/contracts/figures.yml` は figure story 標準契約である。`plan-figure-story` は claim card の `visual_obligations` と figure card の `satisfies_visual_obligations` を対応させ、本文生成前に Figure 1、主図、補足図、missing figure の扱いを決める。個別図は `design-paper-figure` で図の設計意図、reader task、takeaway、encoding、scale/denominator、uncertainty/distribution、caption、runops handoff を Figure design brief として固定する。追加シミュレーションが投稿前に実施可能で予測根拠がある場合は、`draft-predicted-results` が `PREDICTED-RESULT` / `SIM-REQUEST` comment、`xx` 置換条件、`_paperops/requests/analysis/` を伴う予測稿を `manuscript/` の authoring source に作り、Future Work や defensive prose へ早すぎる退避を避ける。`check-predicted-results.py` と `submission-gate` は、submission candidate / round snapshot に予測稿、open AREQ、`xx` が残らないことを確認する。論文固有の figure contract は `_paperops/contracts/figures.yml` overlay へ置く。`figure-story-audit` はその後に、既存図の denominator、path criterion、caption、本文参照を監査する。

section compiler は、`finish-manuscript` から呼ばれる専門 skill 群として Writer の前に走る。`section-contract-check` は Results hierarchy、Discussion functions、Methods definition registry が読者質問、baseline/comparator rationale、判定基準定義を持つかを見る semantic coverage gate である。Results / Discussion はさらに `manuscript/writing-profile.yml` の `section_depth` を参照し、JA は TeX noise を除いた `ja_chars`、EN は TeX noise を除いた `en_words`、段落数、one-paragraph subsections を確認する。これは length is floor, not target の advisory / strict gate であり、短い場合は水増しではなく Results hierarchy や Discussion functions の不足へ戻す。DRAFTED section は `review-block-flow` で block operation table を作り、author stance、reader question、why here、move / split / merge / delete / add を確認してから AUDITED へ進める。`card-coverage-check` は本文中の図、citation、block ID が `_paperops/evidence/` や関連 card に接続されているかを確認し、source summary を claim_boundary、parameter_choice、reviewer_objection、method_precedent の根拠に使う場合は source card に昇格させる。

- `compile-methods-section`: method unit ごとに、本文 / supplement / code への配分、非標準性、結果感度、再実装に必要な情報を決める。
- `compile-results-section`: reader question -> one-sentence answer -> quantitative evidence -> figure -> baseline/comparator rationale -> consequence の順に、結果の読み順を作る。
- `compile-discussion-section`: observation / inference / mechanism_hypothesis / alternative_explanation / implication / prediction / limitation を分ける。

これにより、AI が持っている情報を均等に説明したり、内部 label を本文へ漏らしたり、limitation だけを過剰に複製したりする失敗を減らす。

## workflow state machine

`_paperops/workflow/` は、論文執筆を直列パイプラインではなく階層型状態機械として扱うための状態正本である。全体状態は `SCOPED` から `SUBMISSION_READY` までの固定列を持つが、review 後は一方向に進めず、Issue Router が `evidence_loop`、`story_loop`、`section_loop`、`prose_loop`、`submission_loop` のどこへ戻るかを決める。

各 section は `UNPLANNED`、`PLANNED`、`DRAFTED`、`AUDITED`、`ACCEPTED`、`STALE` の局所状態を持つ。starter の section 依存は空で始め、実際の claim、result、figure、contract が作られた後に `depends_on` へ追加する。upstream artifact が変わった場合は、過去状態へ機械的に戻すのではなく、依存 section を `STALE` にする。たとえば project で `depends_on` に `CLM-0001@...` を持つ section がある場合、`pops workflow invalidate CLM-0001` はその section だけを stale にし、artifact 種別に応じた loop route を付ける。

`_paperops/defaults/workflow/machine.yml` は状態、transition、guard、loop policy の既定規約であり、`_paperops/workflow/current-state.yml` は現在状態である。`workflow-check` は `overall.state` が `POLISHED` なのに section が `DRAFTED` や `STALE` のまま残る不整合も検出する。`_paperops/defaults/workflow/focus-policy.yml` は content / evidence / prose / submission / harness intent の優先順位と許可条件を持つ。`_paperops/defaults/workflow/subagent-roster.yml` は orchestrator が subagent の role、allowed inputs、output、integration decision を管理する契約である。論文固有の workflow 差分が必要な場合だけ `_paperops/workflow/` に同名 overlay を置く。

投稿は二軸で扱う。Authoring axis は `authoring`、`prediction-staged`、`executed`、`reconciled`、`revision-authoring` を持ち、`manuscript/` は常に living authoring source として更新できる。Submission axis は `candidate`、`gated`、`frozen`、`submitted`、`under-review`、`revision-candidate`、`resubmitted` を持ち、`submission/<venue>/round-*` と `_paperops/workflow/submission-ledger.yml` に source commit、gate report、提出 artifact、response package を記録する。

## 設計原則

- 下流作成は `pops init` に統一する。
- `pops update-paperops` はハーネス管理ファイルだけを更新し、下流固有の `story/`、原稿、投稿物、AI 内部 state を自動上書きしない。
- 人間が普段触る入口は prompt、`story/`、`manuscript/`、`submission/`、レビューコメントに寄せる。
- AI が執筆に使う evidence、claim、review、request、refs、workflow、contracts、notes/views は `_paperops/` に閉じる。
- 作業用ドキュメントは原則日本語で書く。識別子、citation key、TOML field name は英語のままでよい。
- raw PDF、未整理ファイル、個人環境の絶対パス、confidential correspondence は tracked な共有ファイルへ混ぜない。
- `paper_ir` や session context のような生成一時物は、明示的な starter artifact でない限り Git 管理しない。
- 検証は strict / advisory / diagnostic を分ける。管理のための checklist を、文章生成の generator として使いすぎない。
