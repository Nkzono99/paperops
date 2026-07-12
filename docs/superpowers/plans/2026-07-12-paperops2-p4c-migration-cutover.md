# PaperOps 2 P4-C Migration and P3 Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** legacy workflow/review stateを保存的にshadow変換し、明示採用・rollback後にP4 projectionをP3 readinessへ接続する。

**Architecture:** migration adapterはlegacy stateを読み、ignored candidate Issue recordsとprojection compareを生成する。adoptionはIssue stateとmanifest workflow modeだけをatomicに切り替え、legacy artifactsを削除・dual-writeしない。

**Tech Stack:** Python 3.11、P2 migration patterns、P4 transaction、P3 compiler、JSON/YAML、unittest、isolated wheel、KUDPC SysB

## Global Constraints

- workflow cutoverはopt-in shadow -> approved adopt、dual-writeなし。
- legacy concern/route/counter/stale/guard/approval/request/human decisionを無言で破棄しない。
- raw confidential reviewer materialはtracked candidateへ入れない。
- P3 scopeをworkflow impactから自動拡張しない。
- legacy removalとdefault cutoverはP7へ残す。

---

### Task 1: Legacy workflow inventory and conservation

**Files:**
- Create: `src/paperops/workflow_v2/migration_inventory.py`
- Create: `src/paperops/workflow_v2/migration_types.py`
- Test: `tests/test_p4_workflow_migration_inventory.py`

**Interfaces:**
- Produces `inventory_legacy_workflow(root) -> WorkflowMigrationInventory` and `validate_workflow_conservation(inventory, candidates)`.

- [ ] Write RED tests for current-state guards/sections/counters, round summary, feedback/request/response cards, approvals, local-only raw review, duplicate IDs, unsafe paths, and deterministic dispositions.
- [ ] Run RED on SysB.
- [ ] Implement bounded readers and dispositions `mapped|deferred|local-only|unsupported` with the same privacy rules as P2/P3.
- [ ] Run Task 1 plus P2 catalog/privacy regressions.
- [ ] Commit: `legacy workflow判断を落とさないためP4 inventoryを追加`

### Task 2: Shadow materializer and comparison

**Files:**
- Create: `src/paperops/workflow_v2/migration.py`
- Test: `tests/test_p4_workflow_migration.py`
- Create: `tests/fixtures/p4/workflow/**`

**Interfaces:**
- Produces: `prepare_workflow_shadow(root, refresh=False) -> WorkflowMigrationResult`.
- Produces public old/new macro, stale, route, issue, approval comparison.

- [ ] Write RED fixture matrix for legacy-only, mixed, typed-only, multi-issue round, scope approval, confidential review, malformed checker/profile, and source drift.
- [ ] Run RED on SysB.
- [ ] Materialize `workflow_issue` candidates and additive round `issue_refs` without modifying tracked files. No route is inferred when legacy data is ambiguous; emit unresolved disposition.
- [ ] Persist canonical report/candidates under `.paperops/workflow/migration/<transaction-id>/`.
- [ ] Run Task 2 and repeat/hash/privacy tests.
- [ ] Commit: `旧新workflowを正本化前に比較できるようshadow変換を追加`

### Task 3: Workflow adoption and rollback

**Files:**
- Create: `src/paperops/workflow_v2/migration_transaction.py`
- Modify manifest workflow-mode support
- Test: `tests/test_p4_workflow_migration_transaction.py`

**Interfaces:**
- Produces `plan_workflow_adoption`, `execute_workflow_adoption`, `recover_incomplete_workflow_migrations`, `plan_workflow_migration_rollback`, `execute_workflow_migration_rollback`.

- [ ] Write RED tests for confirmation, source/candidate drift, validation, snapshot, every failure boundary, manifest workflow mode, repeat no-op, unknown edits, rollback, and no legacy deletion.
- [ ] Run RED on SysB.
- [ ] Implement adoption using P4 durable transaction primitives and `[workflow].mode = legacy|shadow-compare|v2-authoritative` state.
- [ ] Run Task 3 plus P2 adoption/rollback/state tests.
- [ ] Commit: `workflow authorityを明示採用できるようP4 migrationをtransaction化`

### Task 4: Migration CLI

**Files:**
- Modify: `src/paperops/cli/workflow_v2_commands.py`
- Test: `tests/test_p4_workflow_migration_cli.py`

**Interfaces:**
- Adds exact `pops workflow migrate status|diff|adopt|rollback` commands with JSON/human parity.

- [ ] Write parser, non-project, lifecycle, no-confirmation, corruption, repeat, rollback, recovery-order, and private rendering RED tests.
- [ ] Run RED on SysB.
- [ ] Implement thin CLI adapters; bypass update notice and never echo raw exceptions.
- [ ] Run workflow/model/compile/write broad CLI regression.
- [ ] Commit: `P4 opt-in cutoverを一つのworkflow migrate入口へ集約`

### Task 5: P3 readiness integration

**Files:**
- Modify: `src/paperops/compiler/inputs.py`
- Modify: project checker compile-readiness query
- Modify: `src/paperops/compiler/materialize.py`
- Test: `tests/test_p4_p3_integration.py`

**Interfaces:**
- P3 authoritative compile consumes P4 projection only when workflow mode is v2-authoritative.
- Open impacts return exact compile blockers/recompile targets without widening request scope.

- [ ] Write RED tests for open issue target, unrelated issue, stale scientific/editorial/submission approval, resolved impact, Writer receipt verification, issue closure without auto-close, and legacy-mode behavior.
- [ ] Run RED on SysB.
- [ ] Add a whitelisted P4 readiness query to the project checker and snapshot profile/workflow mode/issue hashes as compile inputs.
- [ ] Block selected stale scope, report unaffected scope, and keep P3 compile IDs sensitive to relevant P4 facts only.
- [ ] Run P3 full matrix and existing checker equivalence tests.
- [ ] Commit: `未解決Issueを原稿へ流さないためP4 projectionをP3 readinessへ接続`

### Task 6: Downstream cutover docs, skills, E2E, distribution

**Files:**
- Modify relevant downstream workflow/review/finish/compile skills and wrappers as required
- Modify root/downstream docs, migration, disposition, CHANGELOG, `_handoff/TODO.md`
- Create: `tests/test_p4_documentation.py`
- Create: `tests/test_p4_end_to_end.py`
- Create: `tests/test_p4_distribution.py`

- [ ] Write RED assertions for opt-in mode, five stages, independent issues, owner-local approvals, impact plan/apply, P3 scope boundary, P7 deferral, and exact commands.
- [ ] Update skills so routine routing/closure/approval/recovery uses CLI and AI handles public summaries, reasons, scientific/editorial decisions, and human dialogue.
- [ ] Add source-tree and isolated-wheel E2E: shadow/adopt, multi-issue route, selective stale, approval, P3 compile/write, issue verification/close, publishable projection, rollback.
- [ ] Run every P4/P3/P2 test, workflow/model/Issue/Publication/checker/CLI/distribution regressions, `make cli-smoke`, `make smoke`, and `git diff --check` on SysB.
- [ ] Use `review-template-regression` and `verification-before-completion`; fix all Critical/Important issues and rerun affected/full gates.
- [ ] Commit: `reviewから投稿まで選択的に戻れるようP4 cutoverを完成`
