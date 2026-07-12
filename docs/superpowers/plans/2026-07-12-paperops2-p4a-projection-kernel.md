# PaperOps 2 P4-A Projection Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 六モデルのtyped factから五段階macro stateとselective impactを純粋・決定的に投影する。

**Architecture:** `paperops.workflow_v2`をlegacy `cli/workflow.py`から分離し、profile loader、immutable DTO、catalog graph、projectionの順に構成する。macro stateとeffective staleは保存せず、validated catalogとP3 lineageから算出する。

**Tech Stack:** Python 3.11 standard library、PyYAML、既存model checker、JSON Schema、unittest、KUDPC SysB

## Global Constraints

- macro stateは`INGESTED / MODELED / ARCHITECTED / DRAFTED / PUBLISHABLE`のread-only projectionである。
- review round、submission axis、section state、stale、approvalは直交軸として返す。
- network、AI、tracked file mutationをprojection/planで行わない。
- project-managed checker/profileが欠けた場合にpackage fallbackしない。
- login nodeでtestを実行せず`SysB/2022`の`tssrun`を使う。
- template interface変更にはmigration note、CHANGELOG、`make smoke`を付ける。

---

### Task 1: Workflow DTO and managed profile

**Files:**
- Create: `src/paperops/workflow_v2/__init__.py`
- Create: `src/paperops/workflow_v2/types.py`
- Create: `src/paperops/workflow_v2/profile.py`
- Create: `template/_paperops/defaults/schemas/workflow-profile.schema.json`
- Create: `template/_paperops/defaults/workflow/profile.yml`
- Test: `tests/test_p4_workflow_types.py`

**Interfaces:**
- Produces: `WorkflowFinding`, `WorkflowNode`, `WorkflowEdge`, `ImpactRow`, `WorkflowImpactPlan`, `WorkflowProjection` frozen DTOs.
- Produces: `load_workflow_profile(root: Path) -> WorkflowProfile`.

- [ ] Write failing tests for exact five stages, route enum, registered approval kinds, immutable/canonical DTO output, unknown profile keys, private strings, symlink/special profile, and no package fallback.
- [ ] Run `python3.11 -m unittest tests.test_p4_workflow_types -v` through SysB; expect missing module/profile failure.
- [ ] Implement closed DTO validation and a project-root-held profile loader using the existing safe reader and schema validator. The profile defines route names, target-type rules, approval-kind registry, macro requirements, and impact relations.
- [ ] Run Task 1 plus `tests.test_p3_compiler_types` and schema-profile regression through SysB; expect all pass.
- [ ] Commit: `workflow状態を保存値にしないためP4 projection型を追加`

### Task 2: Typed dependency graph

**Files:**
- Create: `src/paperops/workflow_v2/catalog.py`
- Create: `src/paperops/workflow_v2/graph.py`
- Test: `tests/test_p4_workflow_graph.py`

**Interfaces:**
- Consumes: `WorkflowNode`, `WorkflowEdge`, validated checker catalog query, P3 verified bundle loader.
- Produces: `load_workflow_catalog(root: Path) -> WorkflowCatalogSnapshot`.
- Produces: `build_dependency_graph(snapshot) -> WorkflowGraph`.
- Produces: `plan_workflow_impact(graph, *, changed_ids=(), issue_ids=()) -> WorkflowImpactPlan`.

- [ ] Write failing graph tests covering declared dependencies, claim/result/figure refs, move primary/echo, section/block membership, P3 compile inputs, Publication snapshot refs, cycles, missing/wrong type, direct/transitive/unaffected sets, and deterministic ordering.
- [ ] Run RED on SysB; expect missing graph API.
- [ ] Add a whitelisted project-checker catalog query returning public `{id,type,revision,hash,dependencies}` rows; construct graph edges without importing template scripts into package code.
- [ ] Implement cycle-safe traversal and exact recompile target calculation; unknown/ambiguous references yield findings and no ready plan.
- [ ] Run Task 2, P3 input/materialize/bundle regressions, and checker query isolation on SysB.
- [ ] Commit: `無関係sectionを巻き戻さないためtyped依存graphを構築`

### Task 3: Five-stage projection

**Files:**
- Create: `src/paperops/workflow_v2/projection.py`
- Test: `tests/test_p4_workflow_projection.py`

**Interfaces:**
- Produces: `project_workflow_status(snapshot, graph, profile) -> WorkflowProjection`.

- [ ] Write a table-driven RED matrix for all five stages and independent review/submission/section/stale/approval axes. Include open blocking issue, major issue, stale approval, stale block, active review, rejected story, shadow authority, missing P3 lineage, and publishable candidate.
- [ ] Run RED on SysB.
- [ ] Implement highest-satisfied-stage projection with explicit reason rows. Do not read or write legacy `overall.state` in v2 projection.
- [ ] Add property tests that changing review activity alone does not rewrite macro facts and one claim impact does not stale unrelated sections.
- [ ] Run Task 3 plus existing workflow/model/Publication/P3 tests.
- [ ] Commit: `進行表示と正本を分離するため五段階macro stateを投影`

### Task 4: Read-only workflow status and impact plan CLI

**Files:**
- Create: `src/paperops/cli/workflow_v2_commands.py`
- Modify: `src/paperops/cli/workflow.py`
- Modify: `src/paperops/cli/main.py`
- Test: `tests/test_p4_workflow_cli_readonly.py`

**Interfaces:**
- Adds v2 `pops workflow status [--json]` and `pops workflow plan --changed/--issue [--json]` while retaining legacy parser actions.
- Produces one public `WorkflowCommandResult` and pure renderer.

- [ ] Write parser/result RED tests, unsafe ID/non-project/private exception tests, human/JSON parity, tracked-byte invariance, and update-notice bypass.
- [ ] Run RED on SysB.
- [ ] Implement a preflight that runs P2, P3, and workflow recovery hooks in order, then invokes only projection/plan domain APIs.
- [ ] Persist ready plans canonically below `.paperops/workflow/plans/<plan-id>/plan.json`; plans bind profile/checker/catalog/P3 hashes and contain no prose/raw private values.
- [ ] Run CLI tests plus `tests.test_pops_compile_cli`, `tests.test_pops_write_cli`, and legacy workflow tests.
- [ ] Commit: `定型impact確認をAIから外すためworkflow statusとplanを追加`

### Task 5: P4-A documentation and gate

**Files:**
- Modify: `.gitignore`
- Modify: `template/.gitignore`
- Modify: `docs/architecture.md`
- Modify: `docs/cli.md`
- Modify: `docs/migrations/v0.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_p4a_documentation.py`

**Interfaces:**
- Documents read-only macro state, orthogonal axes, impact plan, ignored storage, and legacy-mode compatibility.

- [ ] Add documentation assertions before edits and run RED on SysB.
- [ ] Update public docs and ignore `.paperops/workflow/` without claiming Issue/approval mutation is available in P4-A.
- [ ] Run all `test_p4_*` available at this point, `make cli-smoke`, and `make smoke` on SysB; run `git diff --check`.
- [ ] Review with `review-template-regression` and fix all Critical/Important findings.
- [ ] Commit: `macro projectionを安全に導入するためP4-A互換境界を文書化`
