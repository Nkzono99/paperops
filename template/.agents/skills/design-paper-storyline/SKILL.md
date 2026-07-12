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

- `_paperops/defaults/contracts/storyline.yml`
- `_paperops/contracts/storyline.yml` if project overlay exists
- `_paperops/defaults/schemas/results-hierarchy.schema.json`
- `_paperops/model/editorial/results-hierarchy.yml`
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/argument-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/scientific-gate.md`
- `_paperops/notes/related-work-map.md`
- `_paperops/notes/reviewer-model.md`
- title / abstract / introduction / Results / Discussion / Conclusion
- figure captions and table captions

## 手順

1. Public-reader として、本文だけから reader_promise、central_claim、scope_boundary を再構成する。
2. Repo-aware editor として、claim / evidence / result-pattern map から evidence_ladder を作る。
3. project-owned の `_paperops/model/editorial/results-hierarchy.yml` に typed Results hierarchy を作る。各 item は安定した `RHI-*` ID と `reader_question`、`answer`、`quantitative_evidence_and_unit_of_analysis`、`figure_table_role`、`baseline_comparator_rationale`、`consequence`、`next_item_id` を持つ。`next_item_id` は配列上の次 item の ID、terminal item では空文字にする。
4. Discussion functions を作る。最低限 `principal_finding`、`mechanism_warrant`、`prior_work_delta`、`alternative_or_boundary`、`implication`、`decisive_next_test` を分ける。
5. Methods definition registry を作る。Results や caption に出る `estimand_and_unit_of_analysis`、`comparison_or_baseline`、`decision_criteria`、`verification_or_convergence` が Methods または初出箇所で定義されるようにする。
6. `_paperops/notes/views/storyline.md` を更新する場合は、`Section depth map` の function と manuscript block を埋める。Results item の値は typed file から複製しない。block が未作成なら `draft` のままにし、本文生成前の blocker として扱う。
7. `scripts/check-storyline.py --root . --strict` と `python scripts/check-section-contracts.py --root . --strict` が通るまで、STRUCTURE_ACCEPTED や Submission hygiene へ進めない。

既存下流 project に `_paperops/model/editorial/results-hierarchy.yml` がない場合は、M0-0003 を採用するまで `storyline.md` の legacy Markdown Results hierarchy を fallback として読める。typed file を作成した後は strict checker がその file を優先するため、成功前に legacy Markdown を削除しない。

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
- `Results hierarchy`: `_paperops/model/editorial/results-hierarchy.yml` の `RHI-*` item と `next_item_id` chain
- `Discussion functions`: principal_finding, mechanism_warrant, prior_work_delta, alternative_or_boundary, implication, decisive_next_test
- `Methods definition registry`: estimand, baseline/comparator, decision criteria, verification の定義位置
- `Content blockers before Submission hygiene`
- `Files to update`

## P3 global replan

P3 Writer candidateは原稿全体をread contextとして持つが、write scopeはcompile時に固定される。candidateを通読してstory spine、section順、argument move、claim roleを変える必要が判明したら、局所TeX patchへ押し込まずEditorial / Results hierarchy / Manuscript Modelを改訂し、人間承認後に`pops compile prepare all`または対象sectionを再実行（再compile）する。`pops compile compare <old> <new>`は候補storyを順位付けせず比較する。

AIは一度作った流れをcandidate全体から何度でも見直してよい。ただし、全体再設計のauthorityはtyped model revisionであり、`pops write`がproseから逆推定して更新しない。routineなsnapshot、scope、conservation、apply、rollbackはCLIへ任せ、storyの意味論はこのskillで明示的に再判断する。

## Codex 実行メモ

- `finish-manuscript` の before-drafting gate として使う。
- `audit-ai-draft`、`peer-review-manuscript`、`review-public-manuscript` で Results / Discussion の薄さを見つけたら、この skill へ戻す。
- `_paperops/notes/views/storyline.md` は controlled authoring view なので、更新したら `make storyline-check` と `make section-contract-check` を実行する。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
