---
id: RS0006
record_type: research_scan
created_at: '2026-05-17T10:44:32+09:00'
status: captured
scope: paperops downstream session continuity
existing_dossier:
classification:
  capability: decision and session continuity checks
  failure_class: decision-log can disappear without readiness signal
evidence:
  local:
  - summary: Open scan noted permanent decisions are required in notes/decision-log.md but the readiness gate did not check that surface.
    ref: template/AGENTS.md; template/CLAUDE.md
  codebase:
  - summary: readiness-check now requires notes/decision-log.md while leaving its internal format flexible.
    ref: template/scripts/readiness-check.py
  - summary: A regression test removes the decision log from a copied template and asserts readiness-check reports the missing file.
    ref: tests/test_readiness_check.py
  external: []
  risk:
  - summary: A strict decision-log schema could create busywork, so the guard only checks file presence and does not enforce entry format.
    ref: template/scripts/readiness-check.py
candidates:
- title: Require notes/decision-log.md in readiness-check
  relation: selected_for_execution
  recommendation: implemented as missing-file guard with regression test
  next_command: python -m unittest tests.test_readiness_check
recommendation: 'record_only: implemented as minimal session-continuity guard; do not build a decision-log CLI unless repeated logging friction appears'
---

# RS0006: readiness-check preserves the decision log surface

## Scope

- scope: paperops downstream session continuity
- existing_dossier: 未設定
- capability: decision and session continuity checks
- failure_class: decision-log can disappear without readiness signal

## Evidence

### Local

- Open scan noted permanent decisions are required in notes/decision-log.md but the readiness gate did not check that surface. (ref: template/AGENTS.md; template/CLAUDE.md)

### Codebase

- readiness-check now requires notes/decision-log.md while leaving its internal format flexible. (ref: template/scripts/readiness-check.py)
- A regression test removes the decision log from a copied template and asserts readiness-check reports the missing file. (ref: tests/test_readiness_check.py)

### External

- なし

### Risk And Counterexample

- A strict decision-log schema could create busywork, so the guard only checks file presence and does not enforce entry format. (ref: template/scripts/readiness-check.py)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Require notes/decision-log.md in readiness-check | selected_for_execution | implemented as missing-file guard with regression test | python -m unittest tests.test_readiness_check |

## Recommendation

record_only: implemented as minimal session-continuity guard; do not build a decision-log CLI unless repeated logging friction appears

## Next Commands

- `python -m unittest tests.test_readiness_check`
