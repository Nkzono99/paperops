---
id: RS0004
record_type: research_scan
created_at: '2026-05-17T09:40:16+09:00'
status: captured
scope: paperops downstream skill discoverability
existing_dossier:
classification:
  capability: project-local skill discoverability
  failure_class: flat skill list increases operator selection burden
evidence:
  local:
  - summary: Open scan found the downstream skill surface powerful but broad; a situation-based index can reduce first-choice friction without deleting skills.
    ref: template/AGENTS.md
  codebase:
  - summary: AGENTS and CLAUDE now group skills by setup, session, writing, sync, review, public checks, external links, and upstream feedback.
    ref: template/AGENTS.md; template/CLAUDE.md
  - summary: The root skill catalog mirrors the same situation-based entry points for maintainers.
    ref: docs/skill-catalog.md
  external: []
  risk:
  - summary: Changing skill lists can become another maintained taxonomy, so the change only adds coarse entry points and keeps every existing skill name and compatibility path.
    ref: docs/skill-catalog.md
candidates:
- title: Add situation-based entry points above the full downstream skill table
  relation: selected_for_execution
  recommendation: implemented as additive docs/template guidance; no new skill or path migration
  next_command: make smoke
recommendation: 'record_only: implemented as additive skill-surface guidance; revisit only if users still choose the wrong first skill'
---

# RS0004: Project skill surface gets situation-based entry points

## Scope

- scope: paperops downstream skill discoverability
- existing_dossier: 未設定
- capability: project-local skill discoverability
- failure_class: flat skill list increases operator selection burden

## Evidence

### Local

- Open scan found the downstream skill surface powerful but broad; a situation-based index can reduce first-choice friction without deleting skills. (ref: template/AGENTS.md)

### Codebase

- AGENTS and CLAUDE now group skills by setup, session, writing, sync, review, public checks, external links, and upstream feedback. (ref: template/AGENTS.md; template/CLAUDE.md)
- The root skill catalog mirrors the same situation-based entry points for maintainers. (ref: docs/skill-catalog.md)

### External

- なし

### Risk And Counterexample

- Changing skill lists can become another maintained taxonomy, so the change only adds coarse entry points and keeps every existing skill name and compatibility path. (ref: docs/skill-catalog.md)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add situation-based entry points above the full downstream skill table | selected_for_execution | implemented as additive docs/template guidance; no new skill or path migration | make smoke |

## Recommendation

record_only: implemented as additive skill-surface guidance; revisit only if users still choose the wrong first skill

## Next Commands

- `make smoke`
