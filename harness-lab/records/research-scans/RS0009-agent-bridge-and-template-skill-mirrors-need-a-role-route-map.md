---
id: RS0009
record_type: research_scan
created_at: '2026-05-18T04:19:01+09:00'
status: captured
scope: paperops root HOPS bridge and downstream scaffold skill surfaces
existing_dossier: extends RS0004 skill discoverability from project-local skills into root HarnessOps bridge and template mirror governance
classification:
  capability: agent skill surface routing and mirror governance
  failure_class: host role and layer confusion can send maintainers to the wrong skill source of truth
evidence:
  local:
  - summary: maintenance lane added root .claude/skills/hops-* wrappers while existing template guidance says .agents are source of truth and .claude are thin wrappers; these are different host/layer surfaces
    ref: .claude/skills;template/AGENTS.md;template/CLAUDE.md
  codebase:
  - summary: docs/skill-catalog documents template .agents/.claude mirroring and make skill-mirror-check validates downstream wrappers, but root HOPS bridge assets are governed by .harnessops/lock.json and update-harness rather than template skill-mirror-check
    ref: docs/skill-catalog.md;template/scripts/check-skill-mirror.py;.harnessops/lock.json
  external: []
  risk:
  - summary: Treating root HOPS bridge, template Codex skills, and template Claude wrappers as one mirror class can cause edits in the wrong layer or duplicate route guidance across agent surfaces
    ref: .agents/skills/hops-update-harness/SKILL.md;template/.agents/skills
candidates:
- title: Create a host/role/layer route map for root HOPS bridge vs template skill mirrors
  relation: queued_for_later
  recommendation: document which tool owns each surface and which smoke/lint validates it
  next_command: hops lab capture --title "Agent skill surface route map" --summary "..." --expected-change "..."
recommendation: 'queued_for_later: candidate should be documentation/guard integration, not a new skill; priority lane should decide whether to capture or fold into update-harness docs'
---

# RS0009: Agent bridge and template skill mirrors need a role route map

## Scope

- scope: paperops root HOPS bridge and downstream scaffold skill surfaces
- existing_dossier: extends RS0004 skill discoverability from project-local skills into root HarnessOps bridge and template mirror governance
- capability: agent skill surface routing and mirror governance
- failure_class: host role and layer confusion can send maintainers to the wrong skill source of truth

## Evidence

### Local

- maintenance lane added root .claude/skills/hops-* wrappers while existing template guidance says .agents are source of truth and .claude are thin wrappers; these are different host/layer surfaces (ref: .claude/skills;template/AGENTS.md;template/CLAUDE.md)

### Codebase

- docs/skill-catalog documents template .agents/.claude mirroring and make skill-mirror-check validates downstream wrappers, but root HOPS bridge assets are governed by .harnessops/lock.json and update-harness rather than template skill-mirror-check (ref: docs/skill-catalog.md;template/scripts/check-skill-mirror.py;.harnessops/lock.json)

### External

- なし

### Risk And Counterexample

- Treating root HOPS bridge, template Codex skills, and template Claude wrappers as one mirror class can cause edits in the wrong layer or duplicate route guidance across agent surfaces (ref: .agents/skills/hops-update-harness/SKILL.md;template/.agents/skills)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Create a host/role/layer route map for root HOPS bridge vs template skill mirrors | queued_for_later | document which tool owns each surface and which smoke/lint validates it | hops lab capture --title "Agent skill surface route map" --summary "..." --expected-change "..." |

## Recommendation

queued_for_later: candidate should be documentation/guard integration, not a new skill; priority lane should decide whether to capture or fold into update-harness docs

## Next Commands

- `hops lab capture --title "Agent skill surface route map" --summary "..." --expected-change "..."`
