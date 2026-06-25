---
view_type: controlled_authoring
source_of_truth:
  - claims/arguments/
  - claims/claims/
  - evidence/
  - contracts/storyline.yml
authoritative_for:
  - story_spine
  - reader_promise
  - evidence_ladder
  - results_hierarchy
  - discussion_functions
---

# Storyline

このファイルは、個別 claim や result を本文へ流し込む前に、論文全体の読者体験を固定する controlled authoring view である。論拠カードの正本は `claims/arguments/`、claim / evidence の正本は `claims/` と `evidence/` に置く。

## Story spine

- reader_promise: 未記入
- central_claim: 未記入
- evidence_ladder: 未記入
- scope_boundary: 未記入
- reader_payoff: 未記入

## Editorial architect pass

原稿が一通り読める状態になったら、本文を直接直す前に editorial architect として次を確認する。

- Results が result inventory ではなく reader question の順に並んでいるか。
- Discussion が limitation の列挙ではなく mechanism_warrant、prior_work_delta、decisive_next_test を持つか。
- Abstract / Results / Discussion / Conclusion の claim scope が同じか。
- Submission hygiene に進む前に manuscript content blocker が閉じているか。

## Evidence ladder

| role | claim / evidence | reader job | manuscript location |
| --- | --- | --- | --- |
| primary_anchor | 未記入 | 中心主張の最初の根拠を理解する | 未記入 |
| mechanism_or_boundary | 未記入 | なぜ成り立つか、どこで壊れるかを理解する | 未記入 |
| robustness_or_scope | 未記入 | どこまで一般化できるかを理解する | 未記入 |
| negative_or_null_case | 未記入 | 何を主張しないかを理解する | 未記入 |

## Section depth map

| function | manuscript block | status |
| --- | --- | --- |
| results_hierarchy | 未記入 | draft |
| mechanism_warrant | 未記入 | draft |
| prior_work_delta | 未記入 | draft |
| decisive_next_test | 未記入 | draft |

## Results hierarchy

- reader question 1:
- one-sentence answer:
- quantitative evidence and unit of analysis:
- figure / table role:
- consequence:

## Discussion functions

- principal_finding:
- mechanism_warrant:
- prior_work_delta:
- alternative_or_boundary:
- implication:
- decisive_next_test:

## Submission hygiene boundary

Submission hygiene は、著者 metadata、投稿先形式、license、Open Research DOI、cover letter などの最終提出面である。Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が未解決なら、これらは作業対象にしない。
