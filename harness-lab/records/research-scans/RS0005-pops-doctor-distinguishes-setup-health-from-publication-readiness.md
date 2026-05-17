---
id: RS0005
record_type: research_scan
created_at: '2026-05-17T09:42:04+09:00'
status: captured
scope: paperops CLI lifecycle guidance
existing_dossier:
classification:
  capability: paperops project health signaling
  failure_class: doctor ok can be mistaken for readiness ok
evidence:
  local:
  - summary: Open scan noted that doctor and readiness-check cover different lifecycle gates but the boundary was easy to miss.
    ref: docs/cli.md
  codebase:
  - summary: cmd_doctor now prints a success-scope line pointing users to make readiness-check before sharing or submission.
    ref: src/paperops/cli/main.py
  - summary: CLI tests assert the doctor scope message is present on initialized projects.
    ref: tests/test_pops_cli.py
  external: []
  risk:
  - summary: Extra doctor output can become noisy, so the message is one line and appears only after doctor succeeds.
    ref: src/paperops/cli/main.py
candidates:
- title: Add doctor scope line and docs note for readiness lifecycle boundary
  relation: selected_for_execution
  recommendation: implemented as CLI/docs clarification without changing checks
  next_command: make cli-smoke
recommendation: 'record_only: implemented as low-risk health-signal clarification; no dossier unless users still confuse doctor with pre-submit readiness'
---

# RS0005: pops doctor distinguishes setup health from publication readiness

## Scope

- scope: paperops CLI lifecycle guidance
- existing_dossier: 未設定
- capability: paperops project health signaling
- failure_class: doctor ok can be mistaken for readiness ok

## Evidence

### Local

- Open scan noted that doctor and readiness-check cover different lifecycle gates but the boundary was easy to miss. (ref: docs/cli.md)

### Codebase

- cmd_doctor now prints a success-scope line pointing users to make readiness-check before sharing or submission. (ref: src/paperops/cli/main.py)
- CLI tests assert the doctor scope message is present on initialized projects. (ref: tests/test_pops_cli.py)

### External

- なし

### Risk And Counterexample

- Extra doctor output can become noisy, so the message is one line and appears only after doctor succeeds. (ref: src/paperops/cli/main.py)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add doctor scope line and docs note for readiness lifecycle boundary | selected_for_execution | implemented as CLI/docs clarification without changing checks | make cli-smoke |

## Recommendation

record_only: implemented as low-risk health-signal clarification; no dossier unless users still confuse doctor with pre-submit readiness

## Next Commands

- `make cli-smoke`
