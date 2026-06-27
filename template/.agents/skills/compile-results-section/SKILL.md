---
name: compile-results-section
description: Use when Results must be planned from claims, evidence, figures, and paper_ir before drafting or revising prose.
---

# compile-results-section

Results を実施順や保有情報順ではなく、読者の疑問順に変換する section compiler。`paper_ir` は生成一時物であり、手書き正本ではない。Writer には card 正本を直接渡しすぎず、必要な claims、evidence、requests、controlled authoring view だけを section plan に圧縮する。

## Inputs

- `_paperops/defaults/contracts/results.yml`
- `_paperops/contracts/results.yml` if project overlay exists
- `_paperops/defaults/contracts/figures.yml`
- `_paperops/contracts/figures.yml` if project overlay exists
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `manuscript/writing-profile.yml`
- necessary claim / evidence / request cards

本文生成前に `plan-figure-story` を通し、state/setup 図、criterion 図、primary evidence 図、mechanism/boundary 図が claim に対して足りているか確認する。既存図だけを監査して `figure_story_fixed` にしない。

## Compile Rule

`compile-results-section` は、各 subsection を `reader question -> one-sentence answer -> quantitative evidence -> figure -> baseline / comparator rationale -> consequence` の順にする。caveat は主張の意味を変える場合だけ置く。

Results の subsection plan は、`reader_question`、`answer`、`evidence`、`baseline_or_comparator_rationale`、`scope`、`consequence` を必ず持つ。baseline、control、reference condition、comparator を使う場合は、それが何を隔離し、何を検証していないかを公開読者向けに書く。run inventory、解析を実施した順の列挙、同じ limitation の反復を topic sentence にしない。

Results hierarchy は、`_paperops/notes/views/storyline.md` の `Section depth map`、`Results hierarchy`、`Methods definition registry` に対応する。図表を並べるだけ、代表値だけを置く、baseline の科学的役割や判定基準を Methods に接続しない、境界条件と感度解析を一段落へ圧縮する場合は section-depth blocker として扱う。

AI Writer が「この claim を強めるために必要な追加作業」「後で埋める」などの authoring intent を Results prose に書きそうな場合は、本文にしない。近傍の `% INTENT:` / `% TODO-PAPER:` comment に残し、追加解析が必要なら `_paperops/requests/` へ切り出す。公開本文として意図的に扱う場合だけ `% paperops: allow-authoring-intent -- reason` を直前に置く。

## Section Depth

`manuscript/writing-profile.yml` の `section_depth` を確認する。`ja_chars` は日本語原稿の TeX noise を除いた文字数、`en_words` は英語原稿の TeX noise を除いた word count として扱う。`length_is_floor_not_target` の原則に従い、短い場合も水増ししない。

`section-depth-check` が Results を short と判定した場合は、subsection を増やすこと自体を目的にしない。reader question、answer、quantitative evidence、comparison、baseline/comparator rationale、scope、consequence のどれが欠けているかを特定し、one-paragraph subsections は統合するか、読者質問に答えるだけの内容を加える。

`section-contract-check` が Results hierarchy や Methods definition registry の不足を返した場合は、文章の水増しではなく `_paperops/notes/views/storyline.md` と Methods / Results plan を更新してから本文へ戻る。

Draft 後は `review-block-flow` で block operation table を作る。各 block の reader_question、author_move、why_here、next_block_expectation を確認し、必要なら keep / move / split / merge / delete / add を行ってから AUDITED 扱いにする。

生成した section plan は必要な場合だけ `.paperops/cache/section-plan-results.yml` に置き、Git 管理しない。本文を生成・修正した後は `make authoring-intent-check` を使い、AI 執筆意図が公開 prose に漏れていないことを確認する。
