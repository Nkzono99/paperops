---
id: FB0005
record_type: imported_feedback
created_at: '2026-05-17T04:11:58+09:00'
status: triaged
source:
  type: local-capture
  original_id: harness-lab/records/research-scans/RS0002-imported-feedback-stubs-need-actionable-content-triage.md
  source_project: paper-harness-template
classification:
  capability: feedback import and lab queue hygiene
  failure_class: redacted-placeholder feedback creates unresolvable queue work
links:
  eval_case:
  issue_url:
---

# FB0005: Imported feedback needs actionable-content gate before dossier

## 概要

Imported feedback records can enter the review queue with only redacted source-bundle placeholders and no local reproduction or expected-change detail. FB0001-FB0003 show that the queue then recommends dossier creation even though the local evidence is insufficient.

## 再現

Review harness-lab/records/feedback/FB0001-github-issue-1.md through FB0003 and run hops lab review queue; each record is triaged and queued for dossier creation but only says to consult the source bundle.

## 期待する上流変更

Before imported_feedback is routed to dossier creation, HOPS should detect whether the record contains actionable local content. Placeholder-only imports should be parked or marked source-missing with a deterministic next action instead of appearing as ordinary unlinked feedback.
