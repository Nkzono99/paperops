---
name: finish-manuscript
description: Use when /goal asks Codex to finish a manuscript from scratch or revise a draft through feedback loops without losing manuscript-content priorities.
---

# finish-manuscript

原稿を「少し直す」のではなく、投稿可能な状態まで進める goal lane。1から書く場合と既存稿を直す場合の両方で、claim / evidence / feedback / peer review / final checks を明示的な feedback loop にする。

この skill は **content-first** で動く。ここでの「投稿可能」は、まず原稿本文の story spine、Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が閉じていることを意味する。著者 metadata、license、Open Research DOI、cover letter、投稿先形式などの **Submission hygiene** は最後の hygiene であり、原稿の中身の blocker を解決しない。

この skill は監督役であり、既存の専門 skill を置き換えない。本文だけを局所修正せず、必要な指摘を `review/feedback/`、`claims/`、`evidence/`、`refs/`、`requests/`、`manuscript/` へ遡って反映する。

Writer に生の card ontology を直接渡さない。本文生成の前に `design-paper-storyline` で editorial architect として `notes/views/storyline.md` を確認し、必要な card と controlled authoring view から `paper_ir` を作り、section compiler で Methods / Results / Discussion の読者向け契約へ変換する。

section contract は文章テンプレートではなく入出力契約として扱う。`contracts/<section>.yml` と `manuscript/writing-profile.yml` を重ね、`plan-section -> draft-section -> audit-section` の順で、読者質問、入力、出力、禁止構造、論文種別 overlay を確認する。

図表は本文生成後の飾りとして扱わない。本文生成前に `plan-figure-story` で claim から visual obligation を作り、`contracts/figures.yml` と `manuscript/writing-profile.yml` の figure requirement を確認し、`figure-obligation-check` で missing figure を検出する。

workflow は直列パイプラインではなく階層型状態機械として扱う。本文編集前に `pops workflow status` と `pops workflow next` を確認し、`UNDER_REVIEW` 後は Issue Router で evidence / story / section / prose / submission loop のどこへ戻るかを決める。

## Orchestrator/subagent mode

subagent を使える環境では、main agent は writer ではなく **orchestrator** として動く。`workflow/subagent-roster.yml` を読み、今の blocker に効く role だけを選んで短い brief を渡す。subagent reports are not manuscript edits: subagent の出力は `subagent_report`、feedback card 案、route recommendation、claim/evidence/section plan 更新案であり、同じ manuscript block を複数 agent に直接編集させない。

標準 role は次の通り。

- `story_architect`: story spine、reader promise、Results hierarchy、Discussion functions を俯瞰し、story_loop / section_loop を判定する。
- `evidence_auditor`: claim、quantity、denominator、assumption、analysis request の不足を evidence_loop へ戻す。
- `results_structure_reviewer`: Results が reader question -> answer -> quantitative evidence -> figure -> consequence になっているかを見る。
- `discussion_function_reviewer`: Discussion が mechanism warrant、prior-work delta、alternative/boundary、implication、decisive next test を持つかを見る。
- `figure_story_reviewer`: visual obligation、main / supplement split、caption と本文参照の欠落を見る。
- `public_reader`: 公開原稿だけを読み、未定義語、読者遷移、再現性ギャップを出す。
- `reviewer_panel`: major / minor / meta-review を分け、blocking concern を feedback loop に戻す。
- `submission_hygienist`: STRUCTURE_ACCEPTED 後にだけ author metadata、license、venue formatting、cover letter、`make pre-submit` を扱う。

main agent は各 `subagent_report` を読んで重複をまとめ、`review/rounds/` の Subagent delegation ledger に delegated_role、target、route recommendation、integration decision を記録する。受理した指摘は `review/feedback/`、`claims/`、`evidence/`、`requests/`、`notes/views/storyline.md`、section plan のどれかへ先に反映し、その後に本文を編集する。`integration decision` は `accepted_to_feedback_card`、`accepted_to_claim_or_evidence_update`、`accepted_to_section_plan`、`deferred_with_reason`、`rejected_with_reason`、`requires_human_decision` のいずれかを使う。

subagent brief には role、target artifact、allowed inputs、forbidden inputs、expected output path、route question、completion signal を入れる。raw confidential reviewer text、未公開データ、個人情報、ローカル絶対パスは、許可と範囲が明示されるまで渡さない。

## Content-first gate

`finish-manuscript` 中は、作業対象を次の順で決める。

1. **Manuscript content**: story spine、Results hierarchy、Discussion functions、claim scope、figure story、major review blocker。
2. **Evidence / claim repair**: quantity denominator、unit of analysis、assumption approval、analysis request、figure obligation。
3. **Prose polish**: claim scope を変えない段落流れ、terminology、mirror。
4. **Submission hygiene**: author metadata、license、Open Research DOI、venue formatting、cover letter、`make pre-submit`。

`STRUCTURE_ACCEPTED` が false、または `storyline_architecture_approved` / `results_hierarchy_defined` / `discussion_functions_defined` が false の間は、Submission hygiene を主作業にしない。`readiness-check --require-submission` の失敗は記録してよいが、原稿本文の blocker より優先しない。

下流 manuscript goal 中に readiness-check、Makefile、workflow、skill、template script の再利用可能な欠陥を見つけた場合、その場で下流ハーネスを改修しない。`feedback-paper-harness` 用に問題・再現・提案を要約し、原稿改善へ戻る。ユーザーが明示的に「下流ハーネスを直して」と依頼した場合だけ例外とする。

### Start self-critique

作業開始時に、本文や metadata を触る前に次を短く書く。これは計画ではなく、局所最適へ逃げないための進路確認である。

- `highest_priority_content_blocker`: 今もっとも大きい manuscript content blocker。
- `next_action_reduces_content_blocker`: 次の作業がその blocker をどう減らすか。
- `deferred_hygiene`: 今は扱わない Submission hygiene / downstream harness 作業。
- `route`: story_loop / section_loop / evidence_loop / prose_loop / submission_loop のどれか。

`workflow/current-state.yml` の `CONTENT_FIRST.next_action_reduces_content_blocker` を満たせない場合、本文編集や Submission hygiene に入らず、`design-paper-storyline`、`integrate-writing-feedback`、または evidence / claim repair へ戻る。

### Course-correction checkpoint

次のいずれかが起きたら、作業を続ける前に進路修正を行う。

- `readiness-check` や `make pre-submit` が author metadata、license、venue formatting を指摘した。
- readiness-check、Makefile、script、workflow、skill など downstream harness を直したくなった。
- 30 分以上、Results hierarchy / Discussion functions / claim scope / figure story を進めずに周辺作業だけをしている。
- 新しい feedback が出て、route が manuscript_only か上位 loop か不明になった。

この checkpoint では `scripts/check-content-first.py --root . --phase progress --intent <content|evidence|prose|submission|harness> --strict` を使う。content blocker が残る間に Submission hygiene や harness だけが changed file なら、その作業を止め、必要なら `feedback-paper-harness` へ要約して原稿へ戻る。

### Completion self-critique

完了宣言の直前に `make finish-manuscript-check` を実行する。`STRUCTURE_ACCEPTED` が未達、または reviewer loop の blocking / major concern が閉じていない場合、`make pre-submit` の一部が通っていても `/goal` を完了しない。

## 最初に決める

`/goal` で使われている場合、goal は「投稿可能な原稿と検証済みの対応記録を作る」と具体化する。途中で広がりすぎたら、今の blocker、次の review loop、Finish criteria の未達項目へ戻る。

- `from-scratch`: 1から執筆する。実質的な原稿がまだ無い、または outline / notes だけがある。
- `revision`: 既存稿がある。PDF、TeX、Word、AI 初稿、人間レビュー、査読コメント、editor decision のいずれかを元に仕上げる。
- `response`: 実査読への改訂と response letter が主目的。`respond-to-peer-review` を主ルートにし、この skill は完成条件を監督する。

最初に読む:

- `manuscript/mirror/status.md`
- `notes/project-brief.md`
- `manuscript/venue.md`
- `notes/views/scientific-gate.md`
- `notes/views/storyline.md`
- `contracts/storyline.yml`
- `notes/views/claim-evidence-map.md`
- `notes/views/result-pattern-map.md`
- `notes/views/concept-terms.md`
- `notes/related-work-map.md`
- `notes/reviewer-model.md`
- `contracts/`
- `contracts/figures.yml`
- `workflow/machine.yml`
- `workflow/current-state.yml`
- `workflow/subagent-roster.yml`
- `workflow/round-summary.yml`
- `workflow/decisions.yml`
- `manuscript/writing-profile.yml`
- `review/feedback/`
- `review/rounds/`
- `review/responses/`
- `requests/`

対象原稿が repo 外にある場合は、先に `import-manuscript` で取り込む。raw confidential reviewer text や雑多な人間入力は `_handoff/` に置き、tracked card には要約、ID、route だけを残す。

`_archives/` は sealed scratch archive であり、通常の from-scratch / revision / peer review loop では読まない。ユーザーが明示的に restore / inspect / compare を頼んだ場合だけ `pops scratch` 経由で扱う。

## Workflow phase

まず `pops workflow status` と `pops workflow next` を実行する。`workflow/current-state.yml` に stale section がある場合、全文改稿へ進まず、該当 section の route を確認する。claim、result、figure、section contract を更新した場合は `pops workflow invalidate <artifact-id>` を実行し、依存 section を `STALE` にする。

全体状態は `SCOPED`、`EVIDENCE_READY`、`STORY_LOCKED`、`SECTION_PLANNED`、`DRAFTED`、`UNDER_REVIEW`、`STRUCTURE_ACCEPTED`、`POLISHED`、`SUBMISSION_READY` を使う。`pops workflow advance <state>` は guard が満たされたときだけ使う。guard を満たさない場合は、文章だけで完了扱いにしない。

### Issue Router

Review 後は、Reviewer にそのまま改稿させない。`review/feedback/` の指摘を見て、まず Issue Router として次のどれかに分類する。

- `evidence_loop`: 数値、比較、収束、対照、artifact provenance が不足している。
- `story_loop`: 中心主張、figure story、結果階層、主図と補足図の切り分けが揺れている。
- `section_loop`: Methods の粒度、Results subsection、Discussion の推論型、section contract が合っていない。
- `prose_loop`: claim scope は変えず、名詞化、冗長、防御表現、段落流れだけを直す。
- `submission_loop`: 引用、開示、投稿先形式、bibliography、Data availability を直す。

`submission_loop` は content-first gate の後段である。Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が未解決なら、`submission_loop` ではなく `story_loop` または `section_loop` へ戻す。

分類したら `pops workflow route-review --issue-class <class>` で戻る深さを確認する。状態へ反映する場合だけ `--apply` を付ける。同じ issue class が既定回数を超えて再発した場合は、人間判断へ戻す。

## paper_ir phase

`paper_ir` は生成一時物であり、手書き正本ではない。`claims/`、`evidence/`、`review/`、`requests/` と `notes/views/` から、Writer に渡す最小 context を section ごとに作る。

`paper_ir` の前に `design-paper-storyline` を使い、editorial architect として `reader_promise`、`central_claim`、`evidence_ladder`、`scope_boundary`、Results hierarchy、Discussion functions を確認する。これが未記入なら、section draft ではなく story_loop / section_loop へ戻す。

各 section は、対応する `contracts/<section>.yml` を読む。`manuscript/writing-profile.yml` に paper type、投稿先、分野別要求があれば契約へ overlay する。生成した section plan は必要な場合だけ `.paperops/cache/section-plan-<section>.yml` に置き、Git 管理しない。

各 IR item には、必要な範囲で次を含める。

- `reader_question`
- `answer`
- `evidence`
- `warrant`
- `role`
- `preceded_by`
- `followed_by`
- `caveat_location`
- `sentence_budget`
- `forbidden_terms`
- `plain_language_terms`

### compile-results

`compile-results` は、結果を実施順や保有情報順ではなく、読者の疑問順に並べる。各 subsection は `reader question -> one-sentence answer -> quantitative evidence -> figure -> consequence` の順にする。caveat は主張の意味を変える場合だけ置く。

Results の subsection plan は、`reader_question`、`answer`、`evidence`、`scope`、`consequence` を必ず持つ。run inventory、解析を実施した順の列挙、同じ limitation の反復を topic sentence にしない。

Results hierarchy は、`notes/views/storyline.md` の `Section depth map` と `Results hierarchy` に対応する。図表を並べるだけ、代表値だけを置く、境界条件と感度解析を一段落へ圧縮する場合は section-depth blocker として扱う。

Results plan の前に `plan-figure-story` を通し、state/setup 図、criterion 図、primary evidence 図、mechanism/boundary 図が claim に対して足りているか確認する。既存図だけを監査して `figure_story_fixed` にしない。

### compile-discussion

`compile-discussion` は、claim を `observation`、`inference`、`mechanism_hypothesis`、`alternative_explanation`、`implication`、`prediction`、`limitation` に分ける。Discussion では新しい実験事実を増やさず、観察から解釈命題、機構、含意、識別可能な予測へ進める。

`observation` には直接 evidence を要求する。`mechanism_hypothesis`、`implication`、`prediction` は Discussion で扱えるが、根拠、確信度、どの limitation がどの claim を弱めるかを明示する。

Discussion functions は、少なくとも `principal_finding`、`mechanism_warrant`、`prior_work_delta`、`alternative_or_boundary`、`implication`、`decisive_next_test` を分ける。Discussion が limitation の列挙だけなら、polish ではなく section-depth blocker として `design-paper-storyline` へ戻す。

### compile-methods

`compile-methods` は、method unit ごとに本文 / supplement / code の配分を決める。非標準か、結果がその選択に敏感か、読者が再実装するために必要か、引用で代替できるかを見て、bookkeeping と物理モデル説明を混同しない。

結果の解釈を変える情報は本文、独立再現に必要だが読み筋を止める情報は supplement、実行ログや file format、乱数台帳は code / manifest へ送る。境界条件、状態量、推定量、収束や検証は `writing-profile.yml` の paper type overlay と照合する。

## From-scratch lane

1から書く場合は、文章生成へ急がず、先に論文としての骨格を作る。

1. `notes/project-brief.md`、`manuscript/venue.md`、`notes/reviewer-model.md` を更新する。
2. 関連研究が弱い場合は `research-related-work` で source cluster と debate matrix を作る。
3. raw result がある場合は `map-result-patterns` で result pattern / evidence packet にする。
4. 中心主張、Abstract、Conclusion、main figure caption の前に `scientific-gate` を通す。
5. `design-manuscript-claims` で core claim、essential results、keep / compress / move / cut を決める。
6. `design-paper-storyline` で story spine、Results hierarchy、Discussion functions を固定する。
7. `plan-figure-story` で本文生成前に visual obligation、Figure 1 role、main / supplement の切り分けを決め、`make figure-obligation-check` を通す。
8. `paper_ir` phase で compile-results / compile-discussion / compile-methods を必要範囲で通す。
9. human approval が必要な assumption、claim scope、投稿先 fit を明示し、承認なしに中心主張へ昇格しない。
10. `manuscript/ja/` を source-of-truth として draft し、必要に応じて `paragraph-surgery` と `polish-ai-draft` で整える。
11. `sync-ja-en`、`figure-story-audit`、`public-terminology-pass`、`concept-term-check`、`ai-disclosure-check` を必要範囲で通す。

## Revision lane

既存稿を仕上げる場合は、まず現稿の読みと feedback を分ける。

1. 既存稿が repo 外なら `import-manuscript` で取り込む。
2. AI 初稿や防御的な文章が目立つ場合、または Results / Discussion が薄い場合は、本文を書き直す前に `audit-ai-draft` と `design-paper-storyline` で論旨、storyline、claim lock を確認する。
3. 人間の TeX diff / inline comment がある場合は `collect-manuscript-review` で review ledger に回収する。
4. 自然文指示、PDF 指摘、査読風コメント、editor / reviewer comments は `integrate-writing-feedback` で feedback card 化する。
5. 指摘が claim、gate、evidence、figure、refs、analysis request に触れるなら、本文編集より前に上流 card を更新する。
6. 実査読への返答が必要なら `respond-to-peer-review` で comment inventory、response matrix、revision plan、response letter を作る。
7. 本文編集は最後に行い、`% block:` ID と source-of-truth 言語を保つ。

## Peer review loop

原稿が一通り読める状態になったら、完成宣言の前に最低 1 回は reviewer loop を回す。

1. `review-public-manuscript` で公開原稿だけを読む。repo 内部ノートで不足説明を補わない。
2. `peer-review-manuscript` で R1 / R2 / R3 の major / minor comments と meta-review を作る。
3. blocking / major concern を `integrate-writing-feedback` に戻し、feedback card、claim / gate / evidence / request、本文の順に反映する。
4. 修正後に同じ reviewer profile で再レビューする。新しい blocking concern が残るなら完成扱いにしない。
5. 実査読コメントへの改訂では、`respond-to-peer-review` の response matrix と manuscript changes を対応させる。

subagent を使える場合でも、confidential な reviewer text、未公開データ、個人情報を渡す前に許可と範囲を確認する。公開原稿だけの模擬査読なら、subagent を reviewer 役に分けてよい。

## Backward propagation

原稿への feedback は、必ず次のどれに属するかを判定する。

- `manuscript_only`: 誤字、局所表現、段落の流れ。
- `claim_scope_change`: 主張が強すぎる、弱すぎる、順序が悪い。
- `storyline_change`: reader_promise、evidence_ladder、Results hierarchy、Discussion functions が揺れている。
- `scientific_gate_reopen`: assumption、数値、比較、再現性、人間承認が未解決。
- `result_card_update`: 数値、分母、条件名、図表、artifact provenance。
- `source_card_update`: 引用、関連研究、反論文献、source verification。
- `analysis_request`: 追加解析、再計算、感度確認、図表差し替え。
- `response_only`: 原稿ではなく response letter で説明する。
- `section_depth_blocker`: Results hierarchy や Discussion functions が薄く、段落修正ではなく section plan へ戻す。
- `results_hierarchy_gap`: Results が図表・条件・実施順の列挙になっている。
- `discussion_function_gap`: Discussion が limitation 羅列で、mechanism_warrant、prior_work_delta、decisive_next_test がない。
- `submission_hygiene_only`: 投稿前 hygiene だけの問題。STRUCTURE_ACCEPTED 後にだけ扱う。

この判定をせずに本文だけを直すと、次の review loop で同じ問題が戻る。`refs/` と `notes/` に作る作業ドキュメントは日本語で書く。

## Finish criteria

次を満たすまで `/goal` を完了にしない。

- 中心主張、Abstract、Conclusion、main figure caption の claim が `scientific-gate` で `ready-to-write` または人間が明示承認した scope になっている。
- `notes/views/storyline.md` が埋まり、`storyline_architecture_approved`、Results hierarchy、Discussion functions が確認されている。
- human approval が必要な assumption、投稿先、claim scope、response stance が未承認のまま残っていない。
- `review/feedback/` と reviewer loop に blocking / major の open item が残っていない。残す場合は defer 理由と本文での scope limit がある。
- 図表、caption、本文参照、claim-evidence map、related work、AI disclosure、reproducibility の不整合が解消されている。
- 概念語ビューで accepted / plain-language / avoid が整理され、表記揺れや過剰な concept-term compression が残っていない。
- 実査読改訂では、comment inventory、response matrix、本文変更、response letter が対応している。
- 原稿本文、mirror、引用、figure reference、layer card、submission drift など、変更範囲に応じたチェックを通している。
- 最終 PDF / TeX / response letter のどれを成果物とするかを明示し、最終 commit または共有すべき artifact を記録している。

## Codex 実行メモ

- `/goal` 中は、今の blocker、次の 1-3 手、Finish criteria の未達項目を短く更新する。
- 作業開始時に Start self-critique、進路変更時に Course-correction checkpoint、完了前に Completion self-critique を行う。
- 進路変更時は `scripts/check-content-first.py --root . --phase progress --intent <intent> --strict`、完了前は `make finish-manuscript-check` を使う。
- content-first gate を毎回確認し、manuscript content blocker が残る間は Submission hygiene を主作業にしない。
- 原稿を編集したら `make mirror-check` を実行する。引用や bibliography に触れたら `make citation-check`、概念語に触れたら `make concept-term-check`、図表に触れたら `make figure-reference-check`、claim / evidence / layer card に触れたら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。
- storyline を更新したら `make storyline-check` を実行する。投稿前には `scripts/check-storyline.py --root . --strict` を使う。
- 図表を本文生成前に設計する場合は `plan-figure-story` と `make figure-obligation-check` を使う。投稿前には `scripts/check-figure-obligations.py --root . --strict` で supported claim に visual obligation または `no_figure_reason` があるか確認する。
- `make pre-submit` は STRUCTURE_ACCEPTED 後の最終確認として使う。テンプレート初期状態や未設定項目で通らない場合も、Results hierarchy / Discussion functions / claim scope の blocker より優先しない。
- 下流 manuscript goal 中に readiness-check、Makefile、script、skill、workflow の再利用可能な改善を思いついたら、実装せず `feedback-paper-harness` へ送る。
- AI が本文、レビュー、response draft に関与した場合は `ai-disclosure-check` を通す。
- 文章を磨くために evidence の弱さを隠さない。`analysis-needed` や `assumption-blocked` は文体ではなく upstream route で処理する。
- raw confidential reviewer text を web 検索語、Issue、公開 PR、tracked notes に入れない。
