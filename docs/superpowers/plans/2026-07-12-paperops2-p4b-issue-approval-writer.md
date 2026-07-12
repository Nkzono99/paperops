# PaperOps 2 P4-B Issue and Approval Writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一review round内の複数Issueを独立route/close/reopenし、owner-local approvalをplan/apply transactionで安全に更新する。

**Architecture:** `workflow_issue`はIssue Modelの独立record、review roundはそのIDを束ねるcontainerとする。proposalはignored plan、authority変更は一つのjournaled workflow transactionだけが行う。

**Tech Stack:** Python 3.11、既存schema/checker kernel、PyYAML、fcntl/fsync/os.replace、unittest、KUDPC SysB

## Global Constraints

- Issueは一つのcurrent routeとimmutable route historyを持ち、round全体routeを持たない。
- approvalは対象所有モデル内に置き、subject revision/hashへ結ぶ。
- proposal commandはtracked stateを変更せず、`workflow apply --yes`だけが変更する。
- unknown human editは上書きしない。dual-writeしない。
- P3 TeX/model/workflow/mirror ledgerをIssue applyから暗黙変更しない。

---

### Task 1: Workflow issue schema and semantics

**Files:**
- Create: `template/_paperops/defaults/schemas/issue-workflow-issue.schema.json`
- Modify: `template/_paperops/defaults/schemas/issue-review-round.schema.json`
- Modify: `template/_paperops/defaults/schemas/registry.yml`
- Modify: `template/scripts/paperops_models.py`
- Test: `tests/test_p4_workflow_issue_model.py`

**Interfaces:**
- Adds record type `workflow_issue`, ID `ISS-[0-9]{4,}`, route/status/history/impact/closure schema.
- Adds optional `issue_refs[]` to review rounds while retaining `feedback_refs[]`.

- [ ] Write schema/semantic RED tests for independent route/status, duplicate/missing round refs, typed target revision/hash, route history, open/resolved/waived impacts, closure, escalation, confidentiality, and public-safe values.
- [ ] Run RED on SysB.
- [ ] Implement closed schema and checker semantics: closed requires all impacts resolved/approved waiver, no blocking deps, current verification refs, and current owner-local waiver approval.
- [ ] Run Task 1 plus Issue/Publication/cross-model/P1-B regressions.
- [ ] Commit: `review指摘を個別に閉じるためworkflow issue recordを追加`

### Task 2: Owner-local approval registry and planner

**Files:**
- Create: `src/paperops/workflow_v2/approvals.py`
- Modify: common approval definitions in managed model schemas
- Modify: `template/scripts/paperops_models.py`
- Test: `tests/test_p4_workflow_approval.py`

**Interfaces:**
- Produces: `inspect_approvals(root, target_id="") -> ApprovalStatusResult`.
- Produces: `plan_approval_decision(root, target_id, kind, decision, reason, profile="") -> WorkflowMutationPlan`.

- [ ] Write RED tests for standard kinds, namespaced profile kinds, target-type allowlist, current/stale/rejected/revoked decisions, approval append without subject revision/hash change, reason privacy, and wrong target.
- [ ] Run RED on SysB.
- [ ] Change approval schema kind to a safe identifier and enforce the managed registry semantically. Preserve all existing standard values and checker codes.
- [ ] Implement pure plan generation bound to subject/model/profile/checker hash; approval history is append-only.
- [ ] Run Task 2 plus Research/Manuscript/Issue/Publication approval regressions and P3 compile readiness.
- [ ] Commit: `承認を対象revisionへ固定するためowner-local approval plannerを追加`

### Task 3: Issue proposal domain

**Files:**
- Create: `src/paperops/workflow_v2/issues.py`
- Test: `tests/test_p4_workflow_issue_domain.py`

**Interfaces:**
- Produces: `inspect_issues(root, issue_id="all")`.
- Produces: `plan_issue_route`, `plan_issue_close`, `plan_issue_reopen` returning `WorkflowMutationPlan`.

- [ ] Write RED tests for multiple issues in one round, independent route/close/reopen, route history, exact impact binding, closure blockers, waiver, escalation, repeat no-op, and unrelated issue invariance.
- [ ] Run RED on SysB.
- [ ] Implement strict loader and planners. Route proposals call P4-A impact planner and embed the deterministic direct/transitive/unaffected summary.
- [ ] Ensure proposal creation changes only ignored plan state and never model/workflow/TeX.
- [ ] Run Task 3 and P4-A tests.
- [ ] Commit: `複数Issueを独立処理するためrouteとclosure proposalを型付け`

### Task 4: Journaled workflow transaction

**Files:**
- Create: `src/paperops/workflow_v2/transaction.py`
- Test: `tests/test_p4_workflow_transaction.py`

**Interfaces:**
- Produces: `plan_workflow_apply(root, plan_id, confirmed=False)`, `execute_workflow_apply`, `recover_incomplete_workflow_transactions`, `plan_workflow_rollback`, `execute_workflow_rollback`.

- [ ] Write failure-injection RED tests for every journal state, stage/snapshot/rename/fsync boundary, multi-model approval/issue writes, known-hash recovery, all-post rollback, corrupt snapshot, unknown edit conflict, repeat apply/rollback, and older overlapping rollback.
- [ ] Run RED on SysB.
- [ ] Implement a dedicated workflow lock and sequence. Reuse neutral durable helpers without importing P2/P3 private state-machine functions.
- [ ] Revalidate profile/checker/catalog/subject/plan immediately before mutation; snapshot every affected tracked file; use same-filesystem no-follow replacements and per-file durable progress.
- [ ] Run Task 4 plus P2/P3 transaction and model state regressions.
- [ ] Commit: `Issueと承認を半端に更新しないためworkflow transactionを追加`

### Task 5: Mutating CLI surface

**Files:**
- Modify: `src/paperops/cli/workflow_v2_commands.py`
- Modify: `src/paperops/cli/workflow.py`
- Test: `tests/test_p4_workflow_cli_mutation.py`

**Interfaces:**
- Adds exact nested `workflow issue status|route|close|reopen`, `workflow approval status|decide`, `workflow apply`, `workflow rollback`.

- [ ] Write exact parser RED tests and complete lifecycle JSON/human tests, confirmation absence, drift, recovery order, private exception, no update notice, legacy/v2 mode behavior.
- [ ] Run RED on SysB.
- [ ] Implement thin adapters. Proposal commands return plan IDs; only apply accepts `--yes`; rollback requires an explicit transaction ID.
- [ ] In v2 mode, legacy `advance|invalidate|route-review` return fixed migration guidance without writes; legacy mode remains byte-compatible.
- [ ] Run CLI, workflow kernel, P3 compile/write, and distribution tests.
- [ ] Commit: `Issue処理と承認を直感的なworkflow CLIへ集約`

### Task 6: P4-B docs and gate

**Files:**
- Modify downstream AGENTS/CLAUDE/README and relevant review/approval skills
- Modify: `docs/architecture.md`, `docs/cli.md`, `docs/migrations/v0.md`, `docs/skill-catalog.md`, `CHANGELOG.md`
- Test: `tests/test_p4b_documentation.py`

- [ ] Add RED documentation assertions for independent issues, owner-local approvals, proposal/apply boundary, and direct TeX preservation.
- [ ] Update interfaces and migration note additively; keep `.claude` wrappers as imports unless their contract changes.
- [ ] Run all P4 tests, CLI/model/P3 transaction regressions, `make cli-smoke`, `make smoke`, and `git diff --check` on SysB.
- [ ] Review with `review-template-regression`; fix every Critical/Important issue.
- [ ] Commit: `AIが定型workflowを再実装しないようP4-B入口を統合`
