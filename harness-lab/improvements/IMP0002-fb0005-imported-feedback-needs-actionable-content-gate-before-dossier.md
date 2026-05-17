---
id: IMP0002
record_type: improvement_dossier
created_at: '2026-05-17T04:12:08+09:00'
updated_at: '2026-05-17T04:14:18+09:00'
status: rejected
source_type: friction
scope: harnessops-core
maturity: investigated
relation: extends
promotion_level: candidate
source_feedback: FB0005
eval_cases:
- E0002
hypotheses:
- H0002
decisions:
- D0003
research_scans: []
classification:
  capability: feedback import and lab queue hygiene
  failure_class: redacted-placeholder feedback creates unresolvable queue work
guard:
  status: not-defined
  path:
investigation:
- created_at: '2026-05-17T04:12:20+09:00'
  kind: codebase
  summary: 'RS0002 and FB0001-FB0003 show a queue hygiene gap: imported placeholder records are triaged but contain only source-bundle references, while review queue treats them as unlinked feedback with a dossier next command. The safer mechanism is an actionable-content gate that routes placeholder-only imports to source-missing or park state before dossier creation.'
  evidence_ref: harness-lab/records/research-scans/RS0002-imported-feedback-stubs-need-actionable-content-triage.md; harness-lab/records/feedback/FB0001-github-issue-1.md; harness-lab/records/feedback/FB0002-github-issue-2.md; harness-lab/records/feedback/FB0003-github-issue-3.md
links:
  issue_url:
---

# IMP0002: FB0005: Imported feedback needs actionable-content gate before dossier

## Status

- status: rejected
- maturity: investigated
- source_type: friction
- scope: harnessops-core
- relation: extends
- promotion_level: candidate
- source_feedback: `FB0005`
- linked_records: `FB0005`, `E0002`, `H0002`, `D0003`

## Source Observation

Source: `harness-lab/records/feedback/FB0005-imported-feedback-needs-actionable-content-gate-before-dossier.md`

# FB0005: Imported feedback needs actionable-content gate before dossier

## 概要

Imported feedback records can enter the review queue with only redacted source-bundle placeholders and no local reproduction or expected-change detail. FB0001-FB0003 show that the queue then recommends dossier creation even though the local evidence is insufficient.

## 再現

Review harness-lab/records/feedback/FB0001-github-issue-1.md through FB0003 and run hops lab review queue; each record is triaged and queued for dossier creation but only says to consult the source bundle.

## 期待する上流変更

Before imported_feedback is routed to dossier creation, HOPS should detect whether the record contains actionable local content. Placeholder-only imports should be parked or marked source-missing with a deterministic next action instead of appearing as ordinary unlinked feedback.

## Target Capability

- capability: feedback import and lab queue hygiene
- failure_class: redacted-placeholder feedback creates unresolvable queue work

## Investigation

- 2026-05-17T04:12:20+09:00 [codebase] RS0002 and FB0001-FB0003 show a queue hygiene gap: imported placeholder records are triaged but contain only source-bundle references, while review queue treats them as unlinked feedback with a dossier next command. The safer mechanism is an actionable-content gate that routes placeholder-only imports to source-missing or park state before dossier creation. (evidence: harness-lab/records/research-scans/RS0002-imported-feedback-stubs-need-actionable-content-triage.md; harness-lab/records/feedback/FB0001-github-issue-1.md; harness-lab/records/feedback/FB0002-github-issue-2.md; harness-lab/records/feedback/FB0003-github-issue-3.md)

## Research Scans

research scan はまだありません。


## Evaluation

### E0002: E0002: FB0005-imported-feedback-needs-actionable-content-gate-before-dossier を評価


- source: `harness-lab/records/eval-cases/E0002-fb0005-imported-feedback-needs-actionable-content-gate-before-dossier.md`

- capability: feedback import and lab queue hygiene

- failure_class: redacted-placeholder feedback creates unresolvable queue work

- manual_eval_yml: `harness-lab/views/eval-results/E0002-manual-score.yml`
- manual_eval_md: `harness-lab/views/eval-results/E0002-manual-score.md`
- scores: impact=4, mechanism_clarity=4, evaluability=4, minimality=3, regression_risk=2, operator_burden=1, anti_theater=5, maintainability=4, privacy_sanitization_risk=1
- notes: Manual evaluation from paperops target lab: FB0001-FB0003 are placeholder-only imported_feedback records with source-bundle references in reproduction and expected-change fields, unclassified capability/failure_class, and queue next_command dossier creation. H0002 directly targets that mechanism and is evaluable with those records plus a terse actionable counterexample. It should not be adopted here without a HOPS core implementation or fixture, but it is a strong candidate for upstream implementation design.


## Hypotheses

### H0002: H0002: E0002-fb0005-imported-feedback-needs-actionable-content-gate-before-dossier の仮説


Source: `harness-lab/records/hypotheses/H0002-e0002-fb0005-imported-feedback-needs-actionable-content-gate-before-dossier.md`


# H0002: E0002-fb0005-imported-feedback-needs-actionable-content-gate-before-dossier の仮説

## 仮説

HOPS import and review-queue routing should require actionable local content before recommending dossier creation for imported_feedback records.

## メカニズム

Detect placeholder-only imported feedback by checking for generic source-bundle reproduction and expected-change text, unclassified capability/failure_class, and absent sanitized local detail; route those records to a source-missing or parked state with a source-request next action instead of dossier creation.

## 最小実装

Add the gate in the imported-feedback review queue path and preserve a way to requeue records once sanitized reproduction and expected-change details are added. Do not mutate existing placeholder records into dossiers.

## 代替案: 削除または統合

Continue leaving placeholder imports as unlinked feedback; this keeps the queue noisy and invites normalization of records with insufficient evidence.

## 期待される利点

Daily lanes stop repeatedly recommending impossible dossier work and maintainers get an explicit next action for redacted imports.

## 想定される欠点

A too-strict gate could park terse but actionable imports, so the check must key on placeholder phrases and missing classification rather than length alone.

## 評価計画

Create a fixture or manual eval with placeholder-only imports like FB0001-FB0003 and a separate terse but actionable import. The queue should park only the placeholder records and still recommend dossier creation for actionable feedback.

## 中止基準

Reject if existing import tooling can reliably hydrate source-bundle details before review queue runs, or if a park/source-missing state cannot be represented without hiding user-visible work.


## Evidence

`harness-lab/views/eval-results/E0002-manual-score.md`

## Guard

- status: not-defined
- path: None

## Links

- issue_url: 未設定

## Open Questions And Next Action

次の実装または評価ステップは、この dossier と紐づく正規化レコードを更新してから再生成してください。

## Decision Log

### D0003: D0003: rejected H0002


Source: `harness-lab/records/decisions/D0003-rejected-h0002.md`


# D0003: rejected H0002

## 判断

rejected

## 理由

Do not adopt in this paperops target repository: the mechanism is clear and manually evaluated, but implementation belongs in HOPS core import/review-queue routing.

## 証拠

E0002 manual score recorded at harness-lab/views/eval-results/E0002-manual-score.yml; RS0002 and FB0001-FB0003 demonstrate placeholder-only imports being queued for dossier creation.

## 回帰リスク

Medium: a gate that is too broad could park terse but actionable imported feedback, so implementation needs a positive counterexample fixture.

## フォローアップ

Route IMP0002 upstream for HOPS core implementation, with placeholder-only and terse-actionable fixtures, then replace this target-repo rejection with an adopted core decision if validated.

## 回帰ガード

ガードパスは指定されていません。非採用判断では省略できますが、採用済み判断では必須です。
