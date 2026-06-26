---
id: GATE-0001
type: scientific_gate
claim_id: CLM-0001
gate_status: draft
required_checks: []
blocking_feedback: []
analysis_requests: []
central_assumptions: []
claim_stress_tests: []
external_validation_gates: []
path_criterion: unchecked
evidence_design: unchecked
approved_writing_scope: ""
human_approval: needed
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Scientific Gate Card

## 判定

- ready-to-write / analysis-needed / assumption-blocked / supplement-only / defer

## Required checks

- independence:
- convergence:
- completion vs equilibrium:
- direct comparator:
- sensitivity:
- path criterion:
- evidence design:
- central assumptions:
- claim stress tests:
- external validation gates:
- validated scope:
- not covered:
- source-check:
- figure audit:
- current figure role:
- reproducibility:

## Block reason

止める理由と、解除に必要な evidence / analysis / human approval を書く。

## Approved writing scope

本文、Abstract、Conclusion、caption で言ってよい表現だけを書く。

## Central assumptions

- assumption ID:
- guarded claims:
- artifact role: measured model / validated solver output / proxy / sensitivity / authoring guard
- solved / not solved:
- upper/lower-bound role:
- manuscript placement:
- status: supported / proxy / sensitivity / unresolved
- required follow-up:

`proxy`、`sensitivity`、probability-like column を持つ artifact は、自然確率や測定済み law として扱わず、本文では limitation / follow-up へ回す。

## Claim stress tests

各 claim component について、stress input、stress outcome、strongest allowed wording、must-not-claim、nearest caveat、source artifacts を書く。

`tracked=true` や numeric anchor があっても、authoring gate の場合は `evidence=false`、`review_closure=false`、`claim_upgrade=false` を明示する。

## External validation gates

外部測定、文献拘束、追加 model validation が必要なものは、claim support ではなく claim upgrade blocker として扱う。

- blocking claim:
- required external evidence:
- allowed wording:
- must-not-claim:
- route: `_paperops/notes/views/research-requests.md` / `_paperops/review/responses/` / `_paperops/claims/gates/`

## Path criterion

release / detachment / ejection / lofting などの path-dependent claim では、endpoint work、cumulative work、energy barrier、from-rest subset、force threshold を分ける。

`W_final > 0`、endpoint force、最大値だけを from-rest reachability の十分条件として書かない。

## Evidence design

count、fraction、percentage、maximum、screening、time-correlated saved snapshots を使う場合は、denominator、unit of analysis、independence caveat、same denominator / same criterion、validated scope、not covered を書く。

partial validation、method sanity、workflow QA、authoring readiness、overclaim consistency audit を full numerical verification として閉じない。

## History

- YYYY-MM-DD:
