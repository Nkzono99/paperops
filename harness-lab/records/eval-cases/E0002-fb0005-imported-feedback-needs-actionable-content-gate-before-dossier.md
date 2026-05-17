---
id: E0002
record_type: eval_case
created_at: '2026-05-17T04:12:34+09:00'
status: active
capability: feedback import and lab queue hygiene
failure_class: redacted-placeholder feedback creates unresolvable queue work
source_feedback: FB0005
---

# E0002: FB0005-imported-feedback-needs-actionable-content-gate-before-dossier を評価

## フィクスチャ

- source_feedback: `harness-lab/records/feedback/FB0005-imported-feedback-needs-actionable-content-gate-before-dossier.md`
- fixture_dir: `harness-lab/records/eval-cases/fixtures/E0002`
- observation: Imported feedback records can enter the review queue with only redacted source-bundle placeholders and no local reproduction or expected-change detail. FB0001-FB0003 show that the queue then recommends dossier creation even though the local evidence is insufficient.

## タスク

`feedback import and lab queue hygiene` の `redacted-placeholder feedback creates unresolvable queue work` を減らす最小変更を設計または実装し、次の再現条件が解消されるか評価してください。

Review harness-lab/records/feedback/FB0001-github-issue-1.md through FB0003 and run hops lab review queue; each record is triaged and queued for dossier creation but only says to consult the source bundle.

## 期待される挙動

Before imported_feedback is routed to dossier creation, HOPS should detect whether the record contains actionable local content. Placeholder-only imports should be parked or marked source-missing with a deterministic next action instead of appearing as ordinary unlinked feedback.

## 合格基準

- `redacted-placeholder feedback creates unresolvable queue work` の再現条件が検出または防止される。
- 提案または実装される変更が source feedback の期待変更に対応している。
- `hops lab eval --case E0002 --manual` の score と notes で採用判断に必要な証拠を説明できる。
- 非公開プロジェクト詳細を追加で要求しない。

## 不合格基準

- `redacted-placeholder feedback creates unresolvable queue work` の再現条件を見逃す。
- source feedback の期待変更と無関係な改善案になる。
- 評価が yml score へ記録されず、採用判断の証拠として追えない。
- 再現または判断に非公開文脈が必要になる。
