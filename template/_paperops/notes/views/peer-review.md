---
view_type: pure_overview
starter_example_rows: true
source_of_truth:
  - _paperops/review/rounds/
  - _paperops/review/feedback/
  - _paperops/review/responses/
authoritative_for:
  - overview
---

# 査読・返答ビュー

このファイルは `_paperops/review/feedback/`、`_paperops/review/rounds/`、`_paperops/review/responses/` のカードを人間が俯瞰するためのビューである。個別コメントの正本は feedback card に置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## Review rounds

| round ID | card | scope | status | blocking concerns | Editorial architecture audit | Subagent delegation ledger | highest-priority route |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RVW-0001 | `_paperops/review/rounds/RVW-0001.md` | section / weekly / pre-submit / peer-review / editor-response | draft | 未記入 | story spine / Results hierarchy / Discussion functions | delegated_role / subagent_report / integration decision / orchestrator | `/integrate-writing-feedback` |

## Feedback matrix

| feedback ID | source | target | issue type | severity | upstream route | status |
| --- | --- | --- | --- | --- | --- | --- |
| FB-0001 | human / reviewer | manuscript block / claim / figure | overclaim / evidence-gap / clarity / refs-needed | major | storyline_change / section_depth_blocker / results_hierarchy_gap / discussion_function_gap / claim_scope_change / scientific_gate_reopen / analysis_request / submission_hygiene_only / manuscript_only | open |

## Response matrix

| response ID | feedback cards | changed claims | changed blocks | closure_status | status |
| --- | --- | --- | --- | --- | --- |
| RSP-0001 | FB-0001 | CLM-0001 | 未記入 | closed / first-pass-addressed / partially-addressed / scope-corrected-open / analysis-open / human-decision-open | draft |

## Closure audit

| comment ID | resolution_route | prose explanation | not_closed_reason | next_required_evidence |
| --- | --- | --- | --- | --- |
| R1-001 | manuscript-change-closed / manuscript-clarified-open-analysis / moved-to-research-request / moved-to-harness-feedback / figure-redesign-open / human-decision-open | 未記入 | 未記入 | 未記入 |

`resolution_route` や `closure_status` の label だけで完了扱いにしない。open research request、未実施の比較、figure redesign、human decision が残る場合は `closed` と分ける。

## 未解決の論点

- 未記入
