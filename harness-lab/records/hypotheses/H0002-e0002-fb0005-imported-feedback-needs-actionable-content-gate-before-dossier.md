---
id: H0002
record_type: hypothesis
created_at: '2026-05-17T04:12:49+09:00'
status: proposed
target_capability: feedback import and lab queue hygiene
source_eval_case: E0002
---

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
