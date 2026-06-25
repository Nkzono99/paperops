---
name: design-paper-storyline
description: Use when a manuscript needs a top-level story spine, Results hierarchy, Discussion depth, or an editorial-architect pass before drafting, revision, or final review.
---

# design-paper-storyline

論文全体の story spine を、個別の claim / evidence / section contract より上位で固定する。目的は、AI が result inventory や submission checklist へ逃げず、読者をどの順番で納得させるかを先に決めることである。

## 使う場面

- Results が図表や条件の列挙になっている。
- Discussion が limitation の列挙だけで、mechanism_warrant、prior_work_delta、decisive_next_test が薄い。
- Abstract / Results / Discussion / Conclusion の claim scope が揺れている。
- `/goal` や finish-manuscript 中に、原稿本文より submission hygiene や readiness-check 改修へ進みそうになった。
- 既存稿を大きく直す前に editorial architect として全体の読み筋を決めたい。

## 最初に読む

- `contracts/storyline.yml`
- `notes/views/storyline.md`
- `notes/views/argument-map.md`
- `notes/views/result-pattern-map.md`
- `notes/views/claim-evidence-map.md`
- `notes/views/scientific-gate.md`
- `notes/related-work-map.md`
- `notes/reviewer-model.md`
- title / abstract / introduction / Results / Discussion / Conclusion
- figure captions and table captions

## 手順

1. Public-reader として、本文だけから reader_promise、central_claim、scope_boundary を再構成する。
2. Repo-aware editor として、claim / evidence / result-pattern map から evidence_ladder を作る。
3. Results hierarchy を作る。各 subsection は `reader question -> one-sentence answer -> quantity and unit of analysis -> figure/table role -> consequence` を持つ。
4. Discussion functions を作る。最低限 `principal_finding`、`mechanism_warrant`、`prior_work_delta`、`alternative_or_boundary`、`implication`、`decisive_next_test` を分ける。
5. `notes/views/storyline.md` を更新する場合は、`Section depth map` の function と manuscript block を埋める。block が未作成なら `draft` のままにし、本文生成前の blocker として扱う。
6. `scripts/check-storyline.py --root . --strict` が通るまで、STRUCTURE_ACCEPTED や Submission hygiene へ進めない。

## Editorial architect gate

Editorial architect は writer ではない。本文を直接書き換える前に、上位の読み筋を判定する。

| 状態 | 判定 | 次の route |
| --- | --- | --- |
| story_spine が未記入 | 章修正ではなく storyline 設計へ戻す | story_loop |
| Results hierarchy がない | Results を書かず、reader question と evidence ladder を作る | section_loop |
| Discussion functions がない | Discussion を磨かず、機構・先行研究差分・次の検証を設計する | section_loop |
| submission metadata だけが未完 | manuscript content が accepted なら Submission hygiene | submission_loop |
| downstream harness gap を発見 | 下流 manuscript goal では直さず `feedback-paper-harness` へ要約 | feedback |

## Course-correction checkpoint から呼ぶ場合

`finish-manuscript` 中に作業が metadata、license、readiness-check、Makefile、script、workflow、skill 改修へ逸れそうになったら、この skill を writer ではなく editorial architect として呼ぶ。判断は一つだけでよい。

- Results hierarchy / Discussion functions / claim scope / figure story の未解決 blocker があるなら、Submission hygiene へ進まない。
- `next_action_reduces_content_blocker` を一文で説明できないなら、局所 edit ではなく story_loop / section_loop / evidence_loop を選ぶ。
- downstream harness gap は `feedback-paper-harness` 用の要約に留め、原稿 repo では本文改善へ戻す。

## Submission hygiene guard

Submission hygiene は最終提出面であり、manuscript content blocker を解決しない。Results hierarchy、Discussion functions、major review blocker、claim scope、figure story が未解決なら、author metadata、license、Open Research DOI、readiness-check の拡張を主作業にしない。

下流 manuscript goal 中に readiness-check、Makefile、workflow、skill、template script の再利用可能な欠陥を見つけた場合、その場で下流修正しない。`feedback-paper-harness` に渡す Issue 素材を作り、原稿改善へ戻る。ユーザーが明示的に「下流ハーネスを直して」と依頼した場合だけ例外とする。

## 出力

- `Story spine`: reader_promise / central_claim / scope_boundary / reader_payoff
- `Evidence ladder`: primary_anchor / mechanism_or_boundary / robustness_or_scope / negative_or_null_case
- `Results hierarchy`: subsection ごとの reader question, answer, quantity, figure/table, consequence
- `Discussion functions`: principal_finding, mechanism_warrant, prior_work_delta, alternative_or_boundary, implication, decisive_next_test
- `Content blockers before Submission hygiene`
- `Files to update`

## Codex 実行メモ

- `finish-manuscript` の before-drafting gate として使う。
- `audit-ai-draft`、`peer-review-manuscript`、`review-public-manuscript` で Results / Discussion の薄さを見つけたら、この skill へ戻す。
- `notes/views/storyline.md` は controlled authoring view なので、更新したら `make storyline-check` を実行する。
