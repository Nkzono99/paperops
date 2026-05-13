---
id: RS0001
record_type: research_scan
created_at: '2026-05-13T17:57:34+09:00'
status: captured
scope: paperops downstream update using PyPI harnessops 0.1.4
existing_dossier:
classification:
  capability: agent-bridge update-harness distribution
  failure_class: packaged-asset-drift and conflict explainability
evidence:
  local:
  - summary: hops update-harness on PyPI harnessops 0.1.4 wrote .agents/skills/hops-update-harness/SKILL.md.new because local skill kept a PyPI fallback line; .new removed only that line.
    ref: .agents/skills/hops-update-harness/SKILL.md
  - summary: The bridge and compact memory skills already guide agents to uvx --from harnessops hops <command>, while update-harness still needs explicit wording locally.
    ref: .agents/skills/harnessops-bridge/SKILL.md
  codebase:
  - summary: paperops now uses update-paperops and low-frequency PyPI update notices; downstream update flow increasingly assumes package distribution rather than editable checkouts.
    ref: src/paperops/cli/main.py
  - summary: HarnessOps lock moved to 0.1.4 and updated bridge hashes without source files changing, leaving the useful signal concentrated in one .new conflict.
    ref: .harnessops/lock.json
  external: []
  risk:
  - summary: Blindly accepting generated .new would remove downstream PyPI fallback guidance; blindly ignoring it can leave lock and packaged asset expectations confusing.
    ref: .agents/skills/hops-update-harness/SKILL.md
candidates:
- title: Propagate PyPI fallback wording into packaged hops-update-harness skill
  relation: extends upstream issue 10
  recommendation: capture or patch upstream asset
  next_command: hops lab capture --title "Packaged update-harness skill lacks PyPI fallback" --summary "..." --expected-change "..."
- title: Improve update-harness conflict explanation for additive local guidance
  relation: new candidate
  recommendation: investigate before proposing
  next_command: hops lab capture --title "update-harness conflicts need clearer local-addition diagnostics" --summary "..." --expected-change "..."
recommendation: capture first candidate as upstream asset fix if issue 10 does not already cover update-harness; park second until another .new conflict repeats
---

# RS0001: PyPI版hops更新時のagent asset driftを扱いやすくする

## Scope

- scope: paperops downstream update using PyPI harnessops 0.1.4
- existing_dossier: 未設定
- capability: agent-bridge update-harness distribution
- failure_class: packaged-asset-drift and conflict explainability

## Evidence

### Local

- hops update-harness on PyPI harnessops 0.1.4 wrote .agents/skills/hops-update-harness/SKILL.md.new because local skill kept a PyPI fallback line; .new removed only that line. (ref: .agents/skills/hops-update-harness/SKILL.md)
- The bridge and compact memory skills already guide agents to uvx --from harnessops hops <command>, while update-harness still needs explicit wording locally. (ref: .agents/skills/harnessops-bridge/SKILL.md)

### Codebase

- paperops now uses update-paperops and low-frequency PyPI update notices; downstream update flow increasingly assumes package distribution rather than editable checkouts. (ref: src/paperops/cli/main.py)
- HarnessOps lock moved to 0.1.4 and updated bridge hashes without source files changing, leaving the useful signal concentrated in one .new conflict. (ref: .harnessops/lock.json)

### External

- なし

### Risk And Counterexample

- Blindly accepting generated .new would remove downstream PyPI fallback guidance; blindly ignoring it can leave lock and packaged asset expectations confusing. (ref: .agents/skills/hops-update-harness/SKILL.md)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Propagate PyPI fallback wording into packaged hops-update-harness skill | extends upstream issue 10 | capture or patch upstream asset | hops lab capture --title "Packaged update-harness skill lacks PyPI fallback" --summary "..." --expected-change "..." |
| Improve update-harness conflict explanation for additive local guidance | new candidate | investigate before proposing | hops lab capture --title "update-harness conflicts need clearer local-addition diagnostics" --summary "..." --expected-change "..." |

## Recommendation

capture first candidate as upstream asset fix if issue 10 does not already cover update-harness; park second until another .new conflict repeats

## Next Commands

- `hops lab capture --title "Packaged update-harness skill lacks PyPI fallback" --summary "..." --expected-change "..."`
- `hops lab capture --title "update-harness conflicts need clearer local-addition diagnostics" --summary "..." --expected-change "..."`
