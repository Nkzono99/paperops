# PaperOps 2 P4 Workflow / Issue / Approval Design

## Status and decision

P4 replaces writable macro workflow state and round-level single-route review handling with owner-local typed facts, independent issues, revision-bound approvals, deterministic impact planning, and a read-only five-stage projection. P4 is opt-in. Migration follows P2: shadow comparison, explicit human approval, atomic adoption, and rollback. It does not dual-write legacy and v2 state.

The selected architecture is a hybrid, not a central workflow aggregate and not full event sourcing:

- Research, Editorial, Results hierarchy, Manuscript, Issue, and Publication continue to own their records.
- Approval records remain inside the model that owns the approved subject.
- Individual actionable issues live in the Issue Model.
- Review rounds group issue references but do not choose one route for the round.
- Dependency impact and macro state are deterministic read-only projections.
- CLI transaction journals provide operational history; they are not a seventh semantic authority.

## Goals

1. Project a stable UI state as `INGESTED -> MODELED -> ARCHITECTED -> DRAFTED -> PUBLISHABLE` without writing that state directly.
2. Route, close, defer, reopen, and escalate multiple issues independently within one review round.
3. Preserve claim-, move-, block-, section-, and submission-level dependencies and selective stale behavior.
4. Bind Scientific scope, Editorial choice, Submission, and profile-specific approvals to exact subject revision/hash.
5. Turn routine discovery, impact calculation, closure checks, journaling, recovery, and rollback into deterministic CLI operations.
6. Preserve P3's whole-manuscript read context, fixed write scope, candidate TeX editing, conservation checks, and human-confirmed apply.
7. Keep legacy workflow/cards and direct human TeX editing until P7 removal criteria are separately satisfied.

## Non-goals

- P4 does not generate scientific or editorial decisions.
- P4 does not infer an issue route from confidential prose without an explicit public-safe issue proposal.
- P4 does not update Research, Editorial, Manuscript, or Publication content merely because an issue was opened.
- P4 does not make macro state a writable authority.
- P4 does not remove `pops workflow next|advance|invalidate|route-review`; those remain compatibility commands until opt-in adoption and later deprecation evidence.
- P4 does not replace P3 compile/write transactions or infer model changes from TeX.

## Architecture

### 1. Owner-local authority

The six P1-B models remain the semantic authorities. P4 introduces no Workflow Model and no global approval ledger.

| Fact | Owner |
| --- | --- |
| scientific scope and scientific approval | Research claim/gate record |
| story choice, argument move, editorial approval | Editorial / Results hierarchy |
| section/block topology, compile lineage | Manuscript |
| actionable issue, route, impacts, closure | Issue |
| review round membership | Issue review-round record |
| candidate/round/submission approval | Publication |
| macro state, stale view, approval status | deterministic projection only |

CLI transactions may update more than one owner atomically only when the requested operation explicitly spans them. A transaction never makes its journal the semantic source of truth.

### 2. Individual workflow issue

Add an Issue Model record family `workflow_issue` with IDs `ISS-0001` and a closed schema. One record is one independently actionable concern. Existing feedback, analysis request, writing request, response, and review-round records remain valid.

Required issue fields:

- common record envelope, dependencies, approvals, extensions, metadata;
- `review_round_ref` (optional), source, confidentiality, public summary, optional opaque local-reference ID;
- typed `targets[] = {kind, id, expected_revision?, expected_hash?}`;
- `severity = info|min|major|blocking`;
- `status = open|planned|in_progress|deferred|resolved|closed|reopened`;
- `current_route = evidence|editorial|manuscript|prose|publication|human_decision`;
- immutable `route_history[]` with route, reason, actor, subject revision/hash, and transaction ID;
- `impacts[]` with target, relation, required action, baseline revision/hash, and `open|resolved|waived` disposition;
- closure criteria, verification refs, blocking dependency refs, and closure decision;
- escalation counter and explicit human-decision requirement.

A review round adds ordered unique `issue_refs[]`. Legacy `feedback_refs[]` remains additive compatibility data. Round status is derived independently from its issue statuses; the round no longer contains a representative `issue_class` or a route that rewinds the whole manuscript.

### 3. Dependency and impact graph

Build a pure graph from validated catalogs and P3 artifacts. Nodes include model objects, Editorial moves, Manuscript sections/blocks, P3 compile bundles, approvals, issues, and Publication candidates. Edges are typed and retain source relation:

- declared `dependencies[]`;
- claim/result/figure/source references;
- section membership and block bindings;
- Editorial move primary/echo bindings;
- compile inputs and Writer packet scope;
- issue targets and issue impacts;
- Publication snapshot references.

`plan_workflow_impact()` accepts changed object IDs and/or issue operations. It returns direct and transitive impacts, invalid approval projections, P3 recompile targets, Publication blockers, and unaffected objects. Unknown or ambiguous references block planning. The planner never mutates model files.

An applied impact plan records exact impact rows in the owning workflow issue. Effective stale state is projected from open impacts plus dependency-hash drift. It does not mass-rewrite every dependent record. A substantive owner update changes the subject revision/hash and naturally makes older approvals stale. Closing an issue requires every impact to be resolved or explicitly waived by a current owner-local approval.

This interpretation preserves the agreed plan/apply split while avoiding a second stale authority: `apply` makes the impact fact authoritative in the Issue Model; `status` projects affected blocks/sections/approvals as stale.

### 4. Owner-local approval

Approval entries remain immutable members of their owning record. Each entry binds:

- approval ID and registered kind;
- decision `approved|rejected|revoked`;
- exact subject ID, revision, and semantic hash;
- actor class and public-safe note;
- optional profile and issue/transaction refs.

The standard kinds are `scientific_scope`, `editorial_choice`, `submission`, `scope_expansion`, `reviewer_response`, `authorship`, `license`, and `external_share`. A managed workflow profile may register additional namespaced kinds. JSON Schema checks shape; semantic validation checks that the kind is registered and allowed for the target type.

Approval append does not increment the approved subject revision and approval arrays remain excluded from the subject semantic hash. Any later semantic subject change invalidates the approval by revision/hash mismatch. Revocation appends a new decision; history is never edited in place.

### 5. Read-only macro projection

`project_workflow_status()` selects the highest satisfied stage and reports all orthogonal axes separately.

- `INGESTED`: the project and managed checker/profile are readable and legacy or typed input inventory exists.
- `MODELED`: required Research, Editorial, Results hierarchy, and Manuscript authority is v2, schema-clean, and dependency-clean.
- `ARCHITECTED`: selected story, moves, section topology, scientific scope, and editorial-choice approvals are current; no open blocking evidence/editorial issue prevents architecture.
- `DRAFTED`: required Manuscript sections have current P3 compile lineage and drafted/audited/accepted effective state; no required block is stale.
- `PUBLISHABLE`: a Publication candidate is current, strict submission gates and snapshot integrity pass, required submission approvals are current, and no open blocking/major issue remains.

Review round, submission axis, section state, open issue counts, stale impacts, and approval status are returned beside the macro stage. Review activity does not create a sixth macro stage and never directly rewinds the projection.

## Public CLI

P4 keeps `pops workflow` as the intuitive entry point and adds structured JSON/human parity. All mutating operations use an ignored plan followed by confirmed apply.

```text
pops workflow status [path] [--json]
pops workflow plan [path] [--changed <OBJECT-ID>]... [--issue <ISS-ID>]... [--json]
pops workflow apply <plan-id> [path] --yes [--json]
pops workflow rollback <transaction-id> [path] [--json]

pops workflow issue status [<ISS-ID>|all] [path] [--json]
pops workflow issue route <ISS-ID> <route> [path] --reason <text> [--json]
pops workflow issue close <ISS-ID> [path] --reason <text> [--json]
pops workflow issue reopen <ISS-ID> [path] --reason <text> [--json]

pops workflow approval status [<TARGET-ID>|all] [path] [--json]
pops workflow approval decide <TARGET-ID> <kind> <approved|rejected|revoked>
    [path] --reason <text> [--profile <name>] [--json]

pops workflow migrate status|diff|adopt|rollback ...
```

`issue route|close|reopen` and `approval decide` create an ignored, immutable plan and return its plan ID; they do not mutate tracked state. `workflow apply --yes` revalidates the plan against current model hashes and applies it transactionally. This keeps all mutations under one confirmation/recovery path. A future convenience `--yes` on proposal commands is deliberately excluded from P4 v1 so proposal and authority change cannot be confused.

Legacy `next|advance|invalidate|route-review` remains available in legacy mode. In v2 mode, `next` becomes a projection hint; the three legacy mutators stop with a migration message rather than dual-writing.

## Storage and transactions

Generated state is ignored:

```text
.paperops/workflow/
  plans/<plan-id>/plan.json
  transactions/<transaction-id>/journal.json
  transactions/<transaction-id>/snapshot/**
  projections/status.json
  migration/<transaction-id>/**
```

Plans bind the workflow profile, checker, model authority, all read object revision/hashes, intended writes, impact graph, approval effects, and source mode. Journals use the P2/P3 states `planned/materialized/validated/snapshotted/replacing/committed/rolled_back/conflict`. Apply uses a workflow lock, no-follow regular-file checks, same-filesystem replacements, per-file durable progress, known-hash recovery, and conservative rollback. Unknown human edits are conflicts and remain untouched.

## Migration

P4 migration is separate from P2 model adoption because it changes runtime workflow authority, not the six model documents themselves.

1. `migrate diff` reads legacy `current-state.yml`, round summary, review/feedback/request cards, typed Issue records, approvals, and dependency state.
2. It generates public-safe `workflow_issue` candidates, review-round `issue_refs`, an approval compatibility report, and old-vs-new macro/stale projections under ignored state.
3. Conservation requires every legacy blocking/major concern, route, counter, stale section, guard, approval, request, and human decision to be mapped, deferred with a target, or local-only for a permitted confidential family.
4. `migrate adopt --yes` validates candidates, snapshots affected Issue records and manifest workflow mode, and atomically switches `[workflow].mode` to `v2-authoritative`.
5. No legacy file is deleted or dual-written. Rollback restores the Issue state and workflow mode. Legacy files remain readable only in legacy mode.

## P3 integration

- P3 compile readiness consumes the P4 projection, not writable guard booleans.
- Open impacts on a selected section/block, stale scientific/editorial approvals, or blocking issues prevent authoritative compile.
- Issue impacts identify exact P3 recompile targets but never widen the compile/write scope automatically.
- A committed P3 Writer transaction can be cited as issue verification, but does not close an issue automatically.
- Issue closure rechecks current living TeX hash, P3 transaction receipt, relevant check results, target revision/hash, and approval state.
- P4 never writes candidate or living TeX.

## Privacy

Tracked Issue records contain public summaries and opaque local-reference IDs only. Raw reviewer correspondence, credentials, local/absolute paths, unpublished raw data, and private attachments stay outside tracked state. Plans, projections, findings, journals, and CLI rendering use the shared P3 privacy/redaction boundary and never echo raw exception text.

## Error handling

- malformed/unknown references: block plan creation;
- source or model drift: block apply and require re-plan;
- stale approval: projected invalid, never silently replaced;
- unresolved impact: block issue close;
- missing/corrupt snapshot: conflict without mutation;
- unknown tracked edit during recovery/rollback: conflict without overwrite;
- failed checker/profile: fixed public finding, no package fallback;
- legacy command in v2 mode: deterministic migration guidance, no write.

## Implementation decomposition

P4 is one architectural phase but three implementation cycles, each independently gated:

1. **P4-A Projection kernel**: workflow profile/schema, catalog graph, impact DTO, macro projection, read-only status/plan, legacy characterization.
2. **P4-B Issue and approval writer**: workflow-issue schema/semantics, review-round issue refs, owner-local approval registry, plan/apply/recovery/rollback, CLI.
3. **P4-C Migration and downstream cutover**: shadow adapter/conservation, adopt/rollback, P3 readiness integration, skills/docs/fixtures/distribution.

P4 is complete only when all three cycles pass full gates. This decomposition limits each implementation plan without changing the single final authority design.

## Verification

Tests must cover:

- all five macro stages and every orthogonal-axis combination;
- macro state non-writability and legacy command compatibility;
- multiple issues in one round with independent route/close/reopen;
- direct/transitive/unaffected impact sets, cycles, missing/wrong-type refs;
- claim/move/block/section selective stale and exact P3 recompile targets;
- owner-local current/stale/rejected/revoked/profile approval variants;
- closure blockers, waivers, escalation, human-decision routing;
- plan/apply drift, confirmation, failure injection, recovery, rollback, repeat no-op;
- private/raw/credential/path redaction and public DOI/software controls;
- legacy shadow conservation, adoption, rollback, no dual-write;
- P3 compile/write equivalence and living-TeX-only mutation boundaries;
- source-tree and isolated-wheel lifecycle;
- `make cli-smoke` and `make smoke` on a compute node.

## Success criteria

- Changing one claim does not stale an unrelated section.
- Multiple issues from one review round can be routed and closed independently.
- No macro state is directly writable in v2 mode.
- Every effective stale or invalid approval has a deterministic reason and source edge.
- No approval survives a semantic subject revision/hash change.
- No mutation occurs without a current plan and explicit confirmation.
- P3 compile/write behavior remains intact and does not receive implicit widened scope.
- Legacy mode, migration rollback, and direct human TeX editing remain available.
