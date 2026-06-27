---
name: compile-discussion-section
description: Use when Discussion must be planned from observations, claims, alternatives, implications, and paper_ir before drafting or revision.
---

# compile-discussion-section

Discussion を observation の繰り返しや limitation 羅列から、解釈命題、機構、含意、識別可能な予測へ変換する section compiler。`paper_ir` は生成一時物であり、手書き正本ではない。

## Inputs

- `_paperops/defaults/contracts/discussion.yml`
- `_paperops/contracts/discussion.yml` if project overlay exists
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/related-work-map.md`
- `_paperops/review/feedback/`
- `manuscript/writing-profile.yml`
- necessary claim / evidence / source cards

Discussion に新しい実験事実を増やさない。新しい数値や図表が必要なら `route-manuscript-feedback` で evidence_loop または section_loop に戻す。

## Compile Rule

`compile-discussion-section` は、claim を `observation`、`inference`、`mechanism_hypothesis`、`alternative_explanation`、`implication`、`prediction`、`limitation` に分ける。

`observation` には直接 evidence を要求する。`mechanism_hypothesis`、`implication`、`prediction` は Discussion で扱えるが、根拠、確信度、どの limitation がどの claim を弱めるかを明示する。

Discussion functions は、少なくとも `principal_finding`、`mechanism_warrant`、`prior_work_delta`、`alternative_or_boundary`、`implication`、`decisive_next_test` を分ける。Discussion が limitation の列挙だけなら、polish ではなく section-depth blocker として `design-paper-storyline` へ戻す。

baseline、control、reference condition、comparator を Results の中心に置いた場合、Discussion ではその control が支える解釈と支えない解釈を分ける。baseline 結果を real-world mechanism claim に拡張する場合は、足りない coupled process、boundary condition、decisive next test を明示する。

AI Writer の作業計画を Discussion prose に混ぜない。`claim を強めるための追加作業` は、公開読者に必要なら `decisive_next_test` や limitation/future work として翻訳し、未解決の執筆意図なら `% INTENT:` / `% TODO-PAPER:` または `_paperops/requests/` へ移す。

## Section Depth

`manuscript/writing-profile.yml` の `section_depth` を確認する。`ja_chars` は日本語原稿の TeX noise を除いた文字数、`en_words` は英語原稿の TeX noise を除いた word count として扱う。`length_is_floor_not_target` の原則に従い、短い場合も文量だけを増やさない。

`section-depth-check` が Discussion を short と判定した場合は、observation の繰り返し、generic limitation、曖昧な prior-work mention で埋めない。どの interpretive function が欠けているかを feedback card または section plan に戻す。

`section-contract-check` が Discussion functions の不足を返した場合は、principal finding、mechanism warrant、prior-work delta、alternative/boundary、implication、decisive next test のどれが本文 block にないかを明示して section_loop に戻す。

生成した section plan は必要な場合だけ `.paperops/cache/section-plan-discussion.yml` に置き、Git 管理しない。本文を生成・修正した後は `make authoring-intent-check` を使い、AI 執筆意図が公開 prose に漏れていないことを確認する。
