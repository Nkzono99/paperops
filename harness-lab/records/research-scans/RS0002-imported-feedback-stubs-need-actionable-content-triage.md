---
id: RS0002
record_type: research_scan
created_at: '2026-05-17T04:08:51+09:00'
status: captured
scope: paperops target lab queue after GitHub issue imports
existing_dossier:
classification:
  capability: feedback import and lab queue hygiene
  failure_class: redacted-placeholder feedback creates unresolvable queue work
evidence:
  local:
  - summary: FB0001-FB0003 are triaged imported_feedback records with unclassified capability/failure_class and bodies that only point to a source bundle; their queue next command is dossier creation but the local record lacks reproduction or expected-change content.
    ref: harness-lab/records/feedback/FB0001-github-issue-1.md; harness-lab/records/feedback/FB0002-github-issue-2.md; harness-lab/records/feedback/FB0003-github-issue-3.md
  codebase:
  - summary: hops lab review queue ranks the three placeholder feedback records as unlinked-feedback, while backlog says there are no accepted feedback items without eval cases, creating a queue item that is visible but not executable from local evidence.
    ref: harness-lab/views/imported-feedback.md; harness-lab/views/backlog.md
  external: []
  risk:
  - summary: Blindly running dossier creation on placeholder imports would turn missing evidence into normalized improvement records; ignoring them leaves daily lanes repeatedly seeing the same unlinked items without a deterministic park/request-source action.
    ref: harness-lab/views/imported-feedback.md
candidates:
- title: Add an actionable-content gate for imported feedback before dossier creation
  relation: new candidate
  recommendation: queue for later HOPS workflow design
  next_command: hops lab capture --title "Imported feedback needs actionable-content gate before dossier" --summary "..." --expected-change "..."
- title: Park FB0001-FB0003 as source-missing until sanitized bundle details are available
  relation: record hygiene
  recommendation: defer direct dossier creation
  next_command: hops lab classify/imported-feedback equivalent park action when CLI supports it
recommendation: 'queued_for_later: design a source-content gate or park action for imported feedback; do not create dossiers for FB0001-FB0003 until sanitized reproduction and expected-change details are available'
---

# RS0002: Imported feedback stubs need actionable-content triage

## Scope

- scope: paperops target lab queue after GitHub issue imports
- existing_dossier: 未設定
- capability: feedback import and lab queue hygiene
- failure_class: redacted-placeholder feedback creates unresolvable queue work

## Evidence

### Local

- FB0001-FB0003 are triaged imported_feedback records with unclassified capability/failure_class and bodies that only point to a source bundle; their queue next command is dossier creation but the local record lacks reproduction or expected-change content. (ref: harness-lab/records/feedback/FB0001-github-issue-1.md; harness-lab/records/feedback/FB0002-github-issue-2.md; harness-lab/records/feedback/FB0003-github-issue-3.md)

### Codebase

- hops lab review queue ranks the three placeholder feedback records as unlinked-feedback, while backlog says there are no accepted feedback items without eval cases, creating a queue item that is visible but not executable from local evidence. (ref: harness-lab/views/imported-feedback.md; harness-lab/views/backlog.md)

### External

- なし

### Risk And Counterexample

- Blindly running dossier creation on placeholder imports would turn missing evidence into normalized improvement records; ignoring them leaves daily lanes repeatedly seeing the same unlinked items without a deterministic park/request-source action. (ref: harness-lab/views/imported-feedback.md)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add an actionable-content gate for imported feedback before dossier creation | new candidate | queue for later HOPS workflow design | hops lab capture --title "Imported feedback needs actionable-content gate before dossier" --summary "..." --expected-change "..." |
| Park FB0001-FB0003 as source-missing until sanitized bundle details are available | record hygiene | defer direct dossier creation | hops lab classify/imported-feedback equivalent park action when CLI supports it |

## Recommendation

queued_for_later: design a source-content gate or park action for imported feedback; do not create dossiers for FB0001-FB0003 until sanitized reproduction and expected-change details are available

## Next Commands

- `hops lab capture --title "Imported feedback needs actionable-content gate before dossier" --summary "..." --expected-change "..."`
- `hops lab classify/imported-feedback equivalent park action when CLI supports it`
