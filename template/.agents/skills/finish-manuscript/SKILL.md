---
name: finish-manuscript
description: Use when /goal asks Codex to finish a manuscript from scratch or revise a draft through feedback loops.
---

# finish-manuscript

原稿を「少し直す」のではなく、投稿可能な状態まで進める goal lane。1から書く場合と既存稿を直す場合の両方で、claim / evidence / feedback / peer review / final checks を明示的な feedback loop にする。

この skill は監督役であり、既存の専門 skill を置き換えない。本文だけを局所修正せず、必要な指摘を `review/feedback/`、`claims/`、`evidence/`、`refs/`、`requests/`、`manuscript/` へ遡って反映する。

Writer に生の card ontology を直接渡さない。本文生成の前に、必要な card と controlled authoring view から `paper_ir` を作り、section compiler で Methods / Results / Discussion の読者向け契約へ変換する。

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
- `notes/views/claim-evidence-map.md`
- `notes/views/result-pattern-map.md`
- `notes/views/concept-terms.md`
- `notes/related-work-map.md`
- `notes/reviewer-model.md`
- `review/feedback/`
- `review/rounds/`
- `review/responses/`
- `requests/`

対象原稿が repo 外にある場合は、先に `import-manuscript` で取り込む。raw confidential reviewer text や雑多な人間入力は `_handoff/` に置き、tracked card には要約、ID、route だけを残す。

`_archives/` は sealed scratch archive であり、通常の from-scratch / revision / peer review loop では読まない。ユーザーが明示的に restore / inspect / compare を頼んだ場合だけ `pops scratch` 経由で扱う。

## paper_ir phase

`paper_ir` は生成一時物であり、手書き正本ではない。`claims/`、`evidence/`、`review/`、`requests/` と `notes/views/` から、Writer に渡す最小 context を section ごとに作る。

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

### compile-discussion

`compile-discussion` は、claim を `observation`、`inference`、`mechanism_hypothesis`、`alternative_explanation`、`implication`、`prediction`、`limitation` に分ける。Discussion では新しい実験事実を増やさず、観察から解釈命題、機構、含意、識別可能な予測へ進める。

### compile-methods

`compile-methods` は、method unit ごとに本文 / supplement / code の配分を決める。非標準か、結果がその選択に敏感か、読者が再実装するために必要か、引用で代替できるかを見て、bookkeeping と物理モデル説明を混同しない。

## From-scratch lane

1から書く場合は、文章生成へ急がず、先に論文としての骨格を作る。

1. `notes/project-brief.md`、`manuscript/venue.md`、`notes/reviewer-model.md` を更新する。
2. 関連研究が弱い場合は `research-related-work` で source cluster と debate matrix を作る。
3. raw result がある場合は `map-result-patterns` で result pattern / evidence packet にする。
4. 中心主張、Abstract、Conclusion、main figure caption の前に `scientific-gate` を通す。
5. `design-manuscript-claims` で core claim、essential results、keep / compress / move / cut を決める。
6. `paper_ir` phase で compile-results / compile-discussion / compile-methods を必要範囲で通す。
7. human approval が必要な assumption、claim scope、投稿先 fit を明示し、承認なしに中心主張へ昇格しない。
8. `manuscript/ja/` を source-of-truth として draft し、必要に応じて `paragraph-surgery` と `polish-ai-draft` で整える。
9. `sync-ja-en`、`figure-story-audit`、`public-terminology-pass`、`concept-term-check`、`ai-disclosure-check` を必要範囲で通す。

## Revision lane

既存稿を仕上げる場合は、まず現稿の読みと feedback を分ける。

1. 既存稿が repo 外なら `import-manuscript` で取り込む。
2. AI 初稿や防御的な文章が目立つ場合は、本文を書き直す前に `audit-ai-draft` で論旨と claim lock を確認する。
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
- `scientific_gate_reopen`: assumption、数値、比較、再現性、人間承認が未解決。
- `result_card_update`: 数値、分母、条件名、図表、artifact provenance。
- `source_card_update`: 引用、関連研究、反論文献、source verification。
- `analysis_request`: 追加解析、再計算、感度確認、図表差し替え。
- `response_only`: 原稿ではなく response letter で説明する。

この判定をせずに本文だけを直すと、次の review loop で同じ問題が戻る。`refs/` と `notes/` に作る作業ドキュメントは日本語で書く。

## Finish criteria

次を満たすまで `/goal` を完了にしない。

- 中心主張、Abstract、Conclusion、main figure caption の claim が `scientific-gate` で `ready-to-write` または人間が明示承認した scope になっている。
- human approval が必要な assumption、投稿先、claim scope、response stance が未承認のまま残っていない。
- `review/feedback/` と reviewer loop に blocking / major の open item が残っていない。残す場合は defer 理由と本文での scope limit がある。
- 図表、caption、本文参照、claim-evidence map、related work、AI disclosure、reproducibility の不整合が解消されている。
- 概念語ビューで accepted / plain-language / avoid が整理され、表記揺れや過剰な concept-term compression が残っていない。
- 実査読改訂では、comment inventory、response matrix、本文変更、response letter が対応している。
- 原稿本文、mirror、引用、figure reference、layer card、submission drift など、変更範囲に応じたチェックを通している。
- 最終 PDF / TeX / response letter のどれを成果物とするかを明示し、最終 commit または共有すべき artifact を記録している。

## Codex 実行メモ

- `/goal` 中は、今の blocker、次の 1-3 手、Finish criteria の未達項目を短く更新する。
- 原稿を編集したら `make mirror-check` を実行する。引用や bibliography に触れたら `make citation-check`、概念語に触れたら `make concept-term-check`、図表に触れたら `make figure-reference-check`、claim / evidence / layer card に触れたら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。
- 投稿直前または大きな改稿後は `make pre-submit` を目標にする。テンプレート初期状態や未設定項目で通らない場合は、失敗理由を完成 blocker として残す。
- AI が本文、レビュー、response draft に関与した場合は `ai-disclosure-check` を通す。
- 文章を磨くために evidence の弱さを隠さない。`analysis-needed` や `assumption-blocked` は文体ではなく upstream route で処理する。
- raw confidential reviewer text を web 検索語、Issue、公開 PR、tracked notes に入れない。
