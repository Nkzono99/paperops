---
id: FB0007
record_type: imported_feedback
created_at: '2026-05-22T04:27:53+09:00'
status: triaged
source:
  type: local-capture
  original_id: RS0012
  source_project: paper-harness-template
classification:
  capability: hops research scan queue command consistency
  failure_class: research_scan next_command points to unsupported investigate source
links:
  eval_case:
  issue_url:
---

# FB0007: Research-scan queue emits unsupported investigate command

## 概要

During priority-improvement lane, review queue/context recommended 'hops lab investigate --from RS0012', but current hops lab investigate only accepts FB/E/H/D/IMP sources and fails for research_scan records. This blocks the intended RS0012 pre-implementation investigation path.

## 再現

Run 'uvx --from harnessops hops lab review context --capability external link privacy and handoff visibility --json', then run the returned 'hops lab investigate --from RS0012 ...' command.

## 期待する上流変更

Either support investigation notes directly from research_scan records or make review queue/context emit a supported next command for RS candidates.
