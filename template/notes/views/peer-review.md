# 査読・返答ビュー

このファイルは `review/feedback/`、`review/rounds/`、`review/responses/` のカードを人間が俯瞰するためのビューである。個別コメントの正本は feedback card に置く。

## Review rounds

| round ID | card | scope | status | blocking concerns | next route |
| --- | --- | --- | --- | --- | --- |
| RVW-0001 | `review/rounds/RVW-0001.md` | section / weekly / pre-submit / peer-review / editor-response | draft | 未記入 | `/integrate-writing-feedback` |

## Feedback matrix

| feedback ID | source | target | issue type | severity | upstream route | status |
| --- | --- | --- | --- | --- | --- | --- |
| FB-0001 | human / reviewer | manuscript block / claim / figure | overclaim / evidence-gap / clarity / refs-needed | major | claim_scope_change / scientific_gate_reopen / analysis_request / manuscript_only | open |

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
