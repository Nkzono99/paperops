---
id: RVW-0001
type: review_round
status: draft
scope: section
artifacts: []
feedback_cards: []
subagent_reports: []
review_profile: ""
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Review Round

## Scope

読んだ PDF、TeX、section、figure、submission slot を書く。

## Summary

読者として見えた中心主張、詰まり、強み、blocking concern をまとめる。

## Editorial architecture audit

- story spine:
- Results hierarchy:
- Discussion functions:
- claim/evidence mismatch:
- highest-priority route:

Results が図表・条件の列挙、または Discussion が limitation 羅列の場合は、prose polish や Submission hygiene ではなく `section_loop` / `story_loop` に戻す。

## Subagent delegation ledger

main agent / orchestrator が subagent に読ませた範囲、`subagent_report`、route recommendation、integration decision を記録する。subagent の指摘は本文編集ではなく、まず feedback card、claim/evidence update、section plan、または human decision に統合する。

| delegated_role | target | subagent_report | route recommendation | integration decision |
| --- | --- | --- | --- | --- |
| story_architect / evidence_auditor / results_structure_reviewer / discussion_function_reviewer / figure_story_reviewer / public_reader / reviewer_panel / submission_hygienist | manuscript block / claim / figure / section | `_paperops/review/rounds/subagent-report-*.md` | story_loop / evidence_loop / section_loop / prose_loop / submission_loop | accepted_to_feedback_card / accepted_to_claim_or_evidence_update / accepted_to_section_plan / deferred_with_reason / rejected_with_reason / requires_human_decision |

## Feedback cards

- FB-0001:

## 次の route

- integrate-writing-feedback / scientific-gate / map-result-patterns / research-related-work / manuscript edit
