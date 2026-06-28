---
id: AREQ-0001
type: analysis_request
status: planned
requested_by: FB-0001
related_claims: []
related_results: []
manuscript_refs: []
figure_panels: []
target_project_link: ""
requested_outputs: []
verification_axes: []
runops_id: ""
analysis_plan_frozen_commit: ""
data_not_seen_before_freeze: unchecked
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Analysis Request

Allowed status: planned | predicted | running | executed | reconciled | abandoned

## 依頼内容

追加解析、再計算、図表生成、感度分析、文献確認などを具体化する。

## Paper context

- なぜ必要か:
- 影響する claim:
- 影響する manuscript block:

## Acceptance criteria

- artifact:
- metric / estimand:
- denominator / unit of analysis:
- independence caveat:
- validated scope:
- not covered:
- provenance:
- result card update:

## Planned analysis

`planned_analysis` は予測稿の補助ではなく、実行前の正本として扱う。

- estimand:
- metric:
- denominator:
- unit_of_analysis:
- comparison:
- inclusion_exclusion:
- decision_criteria:
- stopping_condition:
- outcome_neutral_qc:

## Prediction

`prediction` は実行前の予測根拠と外れた場合の分岐を記録する。

予測稿を使う場合だけ記入する。`EXPECTATION-BASIS` は願望ではなく、既存 run、保存則、scaling、pilot result、文献拘束、既検証 solver の単調性に接続する。

- expected_sign:
- expected_rank_or_range:
- uncertainty:
- basis_sources:
- falsification_branch:
- negative/null route:

## Replacement

`replacement` は authoring source の `xx` と予測 comment を実データへ置換する条件である。

- xx_values:
- figure_panels:
- caption_scope:
- claim_scope:
- comments_to_remove: PREDICTED-RESULT / SIM-REQUEST / EXPECTATION-BASIS / REPLACE-XX

## Provenance after execution

`provenance_after_execution` は実行後に埋める。

- commit:
- run_id:
- artifact_hash:
- doi_or_archive:
- result_card:
- figure_card:

## Reconciliation

`reconciliation` では予測と実結果の照合を記録する。結果が予測と違う場合は、本文を予測へ合わせず、Results hierarchy と claim scope を更新する。

- observed_result:
- confirmed_refuted_mixed:
- deviations:
- updated_cards:
- gate_rerun:
- human_signoff:

## Handoff

runops など外部 project に渡す場合、`_paperops/refs/links.toml` の link ID と、相手側 request ID を書く。

- runops_id: blank / draft:* / queued ID
- draft snippet:
- duplicate check:
- no-execution guarantee:
