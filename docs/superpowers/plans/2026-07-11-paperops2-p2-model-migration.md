# PaperOps 2 P2 Model Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AIや手動YAML操作を使わず、六モデルをmodel単位で検証・shadow比較・atomic採用・rollbackできる`pops model` CLIを実装する。

**Architecture:** CLI-owned authority state、model別deterministic adapter、conservation report、durable transaction journalを分離する。project-managed P1-B checkerをJSON argvで呼び、project-owned modelは検証成功後のrecoverable transactionだけで置換する。

**Tech Stack:** Python 3.11 standard library、PyYAML、argparse、TOML manifest、既存PaperOps Schema Profile v1、`unittest`、KUDPC `tssrun`。

## Global Constraints

- Public commands are exactly `pops model status|validate|diff|adopt|rollback`.
- Models are exactly `research`, `editorial`, `results_hierarchy`, `manuscript`, `issue`, `publication`.
- Authority modes are exactly `legacy-authoritative`, `shadow-compare`, `v2-authoritative`.
- Adapters use no network, AI model, LLM prompt, GitHub API, credential, or absolute-path persistence.
- `--dry-run`, validation failure, and conflict leave tracked state and manifest byte-identical.
- Existing legacy artifacts, TeX, review/request cards, submitted snapshots, and `pops migrate` remain available.
- Tests never run directly on the KUDPC login node; inspect host/modules/partitions and use `tssrun` or `sbatch`.

---

### Task 1: Model authority state and atomic manifest writes

**Files:**

- Create: `src/paperops/model_state.py`
- Modify: `src/paperops/cli/manifest.py`
- Create: `tests/test_model_state.py`
- Modify: `tests/test_pops_cli.py`

**Interfaces:**

- Produces: `MODEL_NAMES`, `AUTHORITY_MODES`, `ModelAuthorityState`, `read_model_states(root)`, `write_model_states(root, states)`, `manifest_bytes(root)`.
- Produces: `write_manifest_data_atomic(path, data)` for later transaction commits.
- Preserves: every unknown manifest section and existing `[detached]`, `[migrations]`, `[upgrade]`, `[cli]` data.

- [ ] **Step 1: Write failing state tests**

Cover absent manifest defaults, exact six entries, invalid mode/hash/transaction values, nested TOML round-trip, unknown-section preservation, atomic temp cleanup, and `write_manifest()` preservation after scaffold update.

- [ ] **Step 2: Run RED on a compute node**

Run:

```sh
python3.11 -m unittest tests.test_model_state tests.test_pops_cli -v
```

Expected: import failure for `paperops.model_state`.

- [ ] **Step 3: Implement immutable model state**

Use:

```python
MODEL_NAMES = (
    "research", "editorial", "results_hierarchy",
    "manuscript", "issue", "publication",
)
AUTHORITY_MODES = (
    "legacy-authoritative", "shadow-compare", "v2-authoritative",
)

@dataclass(frozen=True)
class ModelAuthorityState:
    model_name: str
    mode: str = "legacy-authoritative"
    current_hash: str = ""
    last_shadow_transaction: str = ""
    last_adopt_transaction: str = ""
```

Reject unknown model keys and malformed `sha256:` values as `ModelStateError`; do not silently coerce them.

- [ ] **Step 4: Add atomic manifest serialization**

Write UTF-8 to a sibling temporary file, `flush` + `os.fsync`, preserve mode when replacing an existing manifest, then `os.replace`. Remove temporary files on pre-replace failure.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `model単位のauthorityを安全に保持するためmanifest stateを追加`

### Task 2: Versioned JSON output from the P1-B checker

**Files:**

- Modify: `template/scripts/check-paperops-models.py`
- Create: `src/paperops/model_validation.py`
- Create: `tests/test_model_validation.py`
- Modify: `tests/test_paperops_model_check.py`

**Interfaces:**

- Checker produces JSON object `{schema_version, ok, model, phase, findings, hashes}`.
- `run_model_validation(root, model, phase="all", strict=False) -> ValidationResult` invokes `[sys.executable, checker, ... "--json"]` with no shell.
- `ValidationFinding` preserves `code`, `pointer`, `message`, `severity`.

- [ ] **Step 1: Write failing JSON and runner tests**

Assert human output remains byte-shape compatible, JSON stdout contains no Markdown, error findings retain exact pointers, unknown checker/schema version fails as `validation.version`, missing checker fails as `validation.checker_missing`, and argv handles spaces without shell expansion.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_model_validation tests.test_paperops_model_check -v`.

- [ ] **Step 3: Add `--json` rendering**

Refactor final checker rendering so human and JSON outputs consume the same deduplicated findings and computed hashes. Keep exit status rules unchanged.

- [ ] **Step 4: Implement safe runner**

Use project `scripts/check-paperops-models.py`, require JSON schema version 1, cap captured output, convert malformed output to a stable validation finding, and never print a traceback.

- [ ] **Step 5: Run GREEN, smoke, and commit**

Commit message: `CLIがchecker詳細を隠蔽できるよう検証結果をJSON化`

### Task 3: Migration domain types, safe paths, reports, and snapshots

**Files:**

- Create: `src/paperops/model_migration/__init__.py`
- Create: `src/paperops/model_migration/types.py`
- Create: `src/paperops/model_migration/staging.py`
- Create: `tests/test_model_migration_staging.py`

**Interfaces:**

- Produces immutable `MigrationFinding`, `InventoryItem`, `CandidateDocument`, `MigrationCandidate`, `MigrationReport`, `TransactionPaths`.
- Produces `new_transaction_id(now, entropy)`, `transaction_paths(root, id)`, `write_report(paths, report)`, `snapshot_paths(root, transaction_id, relative_paths)`, `verify_snapshot(...)`.

- [ ] **Step 1: Write failing path/report tests**

Cover transaction ID safety, POSIX/Windows traversal, symlink escape, special files, deterministic JSON, Markdown projection, public-safe sanitization, file modes, snapshot hash mismatch, and no absolute path leakage.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_model_migration_staging -v`.

- [ ] **Step 3: Implement DTOs and canonical report JSON**

Use sorted keys and newline-terminated UTF-8 JSON. Report source locations as project-relative paths plus JSON Pointer/line identity only.

- [ ] **Step 4: Implement snapshot copying and verification**

Use `lstat`, reject symlinks/devices, copy only declared relative paths, and create `manifest.json` containing path, mode, size, and `sha256:<hex>`.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `移行内容を秘密情報なしで復元できるようstaging形式を追加`

### Task 4: Adapter protocol, legacy inventory, and conservation gate

**Files:**

- Create: `src/paperops/model_migration/adapters/__init__.py`
- Create: `src/paperops/model_migration/catalog.py`
- Create: `src/paperops/model_migration/legacy.py`
- Create: `tests/test_model_migration_catalog.py`

**Interfaces:**

- Produces `MigrationInput`, `ModelAdapter` protocol, `adapter_for(model_name)`.
- Produces `load_legacy_card(path)`, `inventory_tree(root, allowed_roots)`, `validate_conservation(source, candidate)`.
- Dispositions are exactly `mapped`, `deferred`, `local-only`, `unsupported`.

- [ ] **Step 1: Write failing inventory tests**

Cover YAML front matter, Markdown tables, duplicate keys/IDs, unknown fields, missing files, path escape, raw/private values, stable source hashes, and one disposition per legacy field family.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_model_migration_catalog -v`.

- [ ] **Step 3: Implement dependency-free structured legacy reader**

Parse only explicit front matter, headings, definition lists, and Markdown tables already used by template cards. Preserve unknown material as `migration.unknown_field`; never infer prose semantics.

- [ ] **Step 4: Implement conservation gate**

Make `unsupported` blocking, require reasons for `deferred` and `local-only`, allow `local-only` only for confidentiality families, and diagnose source drift by stored hashes.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `legacy情報を黙って落とさないためconservation catalogを追加`

### Task 5: Research deterministic adapter

**Files:**

- Create: `src/paperops/model_migration/adapters/research.py`
- Create: `tests/fixtures/migration/research/**`
- Create: `tests/test_research_migration_adapter.py`

**Interfaces:**

- Implements `ResearchAdapter.inventory()` and `ResearchAdapter.materialize()`.
- Emits Research index plus per-ID claim/result/figure/source/scientific_gate documents.

- [ ] **Step 1: Write fixture-first tests**

Map every field family listed in `docs/paperops2-disposition.md`; cover CLM/RES/FIG/SRC/GATE IDs, quantity contracts, approvals/history, provenance, unknown rows, private locations, duplicate IDs, and incomplete gate pairing.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_research_migration_adapter -v`.

- [ ] **Step 3: Implement explicit field maps**

Use tables keyed by legacy heading/field name. Do not invent approval, revision, scope, quantity denominator, provenance, or gate decision; unresolved required values become blocking findings.

- [ ] **Step 4: Validate emitted candidate with P1-B checker**

Materialize into staging, compute semantic hashes/index rows only after record schema validation, then run strict Research validation.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `Research card移行をAIなしで再現するためadapterを追加`

### Task 6: Editorial and Results hierarchy adapters

**Files:**

- Create: `src/paperops/model_migration/adapters/editorial.py`
- Create: `tests/fixtures/migration/editorial/**`
- Create: `tests/test_editorial_migration_adapter.py`

**Interfaces:**

- `EditorialAdapter` emits Editorial Model and companion Results hierarchy in one candidate.
- Existing valid typed Results hierarchy is reused by semantic value, never copied without validation.

- [ ] **Step 1: Write mechanism/boundary/negative fixtures**

Cover candidate selection/rejection, reader transformation, claim roles, move ordering, visual obligations, all legacy Results rows, malformed typed no-fallback, and Results hierarchy multi-item preservation.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_editorial_migration_adapter -v`.

- [ ] **Step 3: Implement explicit structured mapping**

Use typed Results if present and valid; otherwise map every recognizable legacy row. Missing selection reasons, claim IDs, or move edges block adoption instead of being synthesized.

- [ ] **Step 4: Run strict paired validation and hash stability tests**

Assert repeated materialization yields identical semantic hashes and source changes yield `migration.source_changed`.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `story判断とResults順序を保つためEditorial移行を型付け`

### Task 7: Manuscript adapter without prose authority

**Files:**

- Create: `src/paperops/model_migration/adapters/manuscript.py`
- Create: `tests/fixtures/migration/manuscript/**`
- Create: `tests/test_manuscript_migration_adapter.py`

**Interfaces:**

- Emits section/block identity, ordering, JA/EN IDs, operations, compiled provenance, and dependency snapshots.
- Never emits TeX prose into model records.

- [ ] **Step 1: Write failing section/block tests**

Cover all section kinds, mirror IDs, block positions, contract refs, compile manifests, dependency hash, manual TeX edits, missing Research approvals, and prose exclusion.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_manuscript_migration_adapter -v`.

- [ ] **Step 3: Implement structural adapter**

Read section contracts, block markers, mirror ledger, and compiler records. Treat absent lineage or unresolved Research refs as blockers; keep human-edited TeX untouched.

- [ ] **Step 4: Run GREEN and commit**

Commit message: `本文を上書きせず構造だけ移行するためManuscript adapterを追加`

### Task 8: Issue and Publication adapters with confidentiality and immutability

**Files:**

- Create: `src/paperops/model_migration/adapters/issue.py`
- Create: `src/paperops/model_migration/adapters/publication.py`
- Create: `tests/fixtures/migration/issue/**`
- Create: `tests/fixtures/migration/publication/**`
- Create: `tests/test_issue_migration_adapter.py`
- Create: `tests/test_publication_migration_adapter.py`

**Interfaces:**

- Issue emits feedback/analysis_request/writing_request/response/review_round records.
- Publication emits aggregate candidate/round state referencing existing artifacts without copying them.

- [ ] **Step 1: Write failing lifecycle and ledger tests**

Cover analysis prediction/execution/reconciliation, closure audit, multiple issues, raw reviewer text, local reference IDs, candidate/round axes, immutable submitted rounds, artifact hashes, and source commit.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_issue_migration_adapter tests.test_publication_migration_adapter -v`.

- [ ] **Step 3: Implement Issue mapping and sanitization**

Reject raw confidential text and local paths; preserve public summaries, opaque local IDs, delegation, integration, closure criteria, and human decisions.

- [ ] **Step 4: Implement Publication ledger mapping**

Never modify submitted artifacts. Require candidate/round identity, source commit, gate report, snapshot manifest, response refs, and immutable marker; unresolved prediction blocks candidate adoption.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `査読機密と投稿証跡を守るためIssueとPublication移行を分離`

### Task 9: `pops model status`, `validate`, and `diff`

**Files:**

- Create: `src/paperops/cli/model_commands.py`
- Modify: `src/paperops/cli/main.py`
- Create: `tests/test_pops_model_cli.py`

**Interfaces:**

- `add_model_parser(subcommands)` registers exactly five public actions.
- Domain result is rendered by `render_model_result(result, json_output)`.
- `diff` persists a shadow transaction and advances only CLI-owned mode/metadata.

- [ ] **Step 1: Write failing parser/output tests**

Cover help, all model names, unknown model/action exit 2, non-project invocation, human/JSON parity, status defaults, validate findings, refresh/no-refresh, and no project-owned mutation.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_pops_model_cli -v`.

- [ ] **Step 3: Implement status and validate**

Resolve project root, run recovery preflight, read exact state, calculate dependency blockers, and render actionable output.

- [ ] **Step 4: Implement diff orchestration**

Inventory → materialize → candidate validation → conservation → report → atomic manifest shadow metadata. Failed diff writes a report but does not advance mode.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `定型model作業を一つの入口へ隠すためpops modelを追加`

### Task 10: Recoverable adopt transaction and crash recovery

**Files:**

- Create: `src/paperops/model_migration/transaction.py`
- Create: `tests/test_model_migration_transaction.py`
- Modify: `src/paperops/cli/model_commands.py`

**Interfaces:**

- Produces `TransactionJournal`, `plan_adoption`, `execute_adoption`, `recover_incomplete_transactions`.
- Journal states are exactly `planned`, `materialized`, `validated`, `snapshotted`, `replacing`, `committed`, `rolled_back`, `conflict`.

- [ ] **Step 1: Write crash-injection tests**

Inject failure before/after every journal transition. Assert tracked/manifest byte identity before replace, automatic snapshot restoration after replace, unknown manual edits produce `recovery.conflict`, and repeat adoption is a no-op.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_model_migration_transaction -v`.

- [ ] **Step 3: Implement durable journal and preflight**

Use canonical JSON temp+fsync+replace, same-filesystem staging, source/candidate drift checks, strict checker gate, and snapshot verification before target replacement.

- [ ] **Step 4: Implement `adopt` CLI**

Require `--yes` outside dry-run, include Results hierarchy with Editorial, block Publication prerequisites, and update manifest only after target replacement succeeds.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `途中停止でも旧stateへ戻せるようmodel adoptionをtransaction化`

### Task 11: Rollback, dependent blocking, and explicit cascade

**Files:**

- Modify: `src/paperops/model_migration/transaction.py`
- Modify: `src/paperops/cli/model_commands.py`
- Create: `tests/test_model_migration_rollback.py`

**Interfaces:**

- Produces `MODEL_DEPENDENCIES`, `dependent_models`, `plan_rollback`, `execute_rollback`.
- Cascade order is reverse topological and included in one journal/snapshot set.

- [ ] **Step 1: Write failing rollback tests**

Cover latest/specific transaction, corrupted snapshot, missing snapshot, blocked dependent, `--cascade`, Editorial companion, dry-run identity, manual edit conflict, and rollback repeat no-op.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_model_migration_rollback -v`.

- [ ] **Step 3: Implement safe rollback plan and execution**

Verify current model/hash and snapshot hashes before any replacement. Restore targets in reverse dependency order and restore/advance manifest atomically through the journal protocol.

- [ ] **Step 4: Run GREEN and commit**

Commit message: `依存modelを壊さず戻せるよう明示rollbackを追加`

### Task 12: Migration fixtures, distribution, documentation, and final review

**Files:**

- Create: `tests/fixtures/migration/mixed/**`
- Create: `tests/test_p2_migration_fixtures.py`
- Create: `tests/test_p2_documentation.py`
- Modify: `tests/test_pops_cli.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli.md`
- Modify: `docs/current-specification.md`
- Modify: `docs/migrations/v0.md`
- Modify: `docs/skill-catalog.md`
- Modify: `docs/paperops2-disposition.md`
- Modify: `template/README.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `CHANGELOG.md`
- Modify: `_handoff/TODO.md` (ignored local ledger)

**Interfaces:**

- Documents the five public commands, model dependency order, report locations, no-AI boundary, dry-run, recovery, rollback, and P3/P4 deferral.
- Wheel-installed CLI must operate on a copied scaffold using its project-managed checker.

- [ ] **Step 1: Write failing end-to-end fixture tests**

Cover legacy-only, typed-only, mixed, modified managed checker, existing project-owned state, partial missing, unknown field, private raw data, submitted round, source-tree CLI, and built-wheel CLI.

- [ ] **Step 2: Run RED**

Run `python3.11 -m unittest tests.test_p2_migration_fixtures tests.test_p2_documentation tests.test_pops_cli -v`.

- [ ] **Step 3: Update all public interfaces and migration notes**

State that deterministic CLI handles routine work, AI handles scientific/editorial judgment only, M0-0005 remains guide-only, and P2 does not remove legacy writers.

- [ ] **Step 4: Run full verification on a compute node**

Run focused P2 tests, all P1/P2 tests, `make cli-smoke`, and `make smoke`. Confirm `git diff --check`, clean generated-file status, no absolute paths/private fixtures, and no writes outside intended fixture temporaries.

- [ ] **Step 5: Review the complete P2 range**

Use `review-template-regression`; fix every Critical/Important issue and rerun focused tests plus smoke.

- [ ] **Step 6: Commit documentation/final fixes**

Commit message: `AIなしで安全にmodel移行できるようP2利用面を完成`

## Execution order and checkpoints

Execute Tasks 1–4 as the migration kernel, Tasks 5–8 as adapter acceptance units, Tasks 9–11 as the public/transactional CLI, and Task 12 as full integration. After every task, record RED/GREEN job IDs in `.superpowers/sdd/progress.md`; do not push or release.
