# PaperOps 2 P3 Typed Compiler / Writer Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** validated typed modelsから全体文脈を失わないWriter packetとcandidate TeXを生成し、scope・意味保存・manual editを検査した承認済みpatchだけをliving TeXへatomicに適用できるP3を完成する。

**Architecture:** `_paperops/model/`はread-only authority、`.paperops/compile/`と`.paperops/writer/`は再生成可能なignored state、`manuscript/`はhuman-edited authorityとして分離する。Compilerはproject-managed checkerでauthority inputを検証し、canonical DTOからbyte-stable bundleを生成する。Writerは全原稿copyを直接編集できるが、deterministic checkerとjournaled applicatorがwrite scope、base hash、mirror、conservationを強制する。

**Tech Stack:** Python 3.11 standard library、PyYAML、argparse、project-managed PaperOps model checker、JSON/YAML/TOML、unittest、KUDPC SysB / Slurm

## Global Constraints

- CLI/checkerはnetwork、AI model、API keyを暗黙利用しない。
- P3はResearch / Editorial / Results hierarchy / Manuscript Model、P2 authority mode、workflow state、mirror freshness ledgerを暗黙更新しない。
- `authoritative` compileは4 modelすべての`v2-authoritative`整合を要求し、`shadow` compileからtracked applyを禁止する。
- compile/start/check/diffはtracked fileをbyte単位で変更しない。
- Writerはcandidate workspace内のTeXを直接編集でき、全原稿をread contextに持つ。
- write scopeは`block / section / manuscript`で、scope外変更と未計画topologyを拒否する。
- apply / rollbackはsnapshot、hash、journalを使い、unknown manual edit時に上書きしない。
- generated bundle、packet、workspace、patch、judge outputをGit管理しない。
- legacy writer、existing skill名、Make gate、strict/advisory semanticsを削除・変更しない。
- `.agents`をskill正本、`.claude`をwrapperとして同時更新する。
- template user interface変更にはmigration noteとCHANGELOGを付け、`make smoke`を通す。
- login nodeでtest payloadを直接実行せず、`tssrun -p gr20001b`でSysB計算ノードへrouteする。
- push / releaseは明示依頼まで行わない。

---

### Task 1: Canonical P3 DTO and confined storage

**Files:**

- Create: `src/paperops/compiler/__init__.py`
- Create: `src/paperops/compiler/types.py`
- Create: `src/paperops/compiler/storage.py`
- Create: `tests/test_p3_compiler_types.py`

**Interfaces:**

- Produces: `CompileFinding`, `InputSnapshot`, `AuthoritySnapshot`, `WriteScope`, `CompileRequest`, `SectionPlan`, `WriterPacket`, `CompileBundle`, `CompilePaths`, `WriterPaths`。
- Produces: `canonical_json_bytes(value) -> bytes`, `semantic_hash(value) -> str`, `compile_paths(root, compile_id)`, `writer_paths(root, session_id)`, `atomic_write_json(path, value)`。
- Enforces: IDs match `^[A-Za-z0-9][A-Za-z0-9._-]*$`; paths stay below `.paperops/compile/` or `.paperops/writer/`; JSON is sorted, UTF-8, newline-terminated, finite and path-safe。

- [ ] **Step 1: Write failing DTO/storage tests**

Create tests that instantiate a minimal `WriteScope` and assert canonical equality under mapping order, semantic hash changes under ordered-list change, unsafe IDs/traversal fail, atomic JSON is newline-terminated, and no absolute path can enter `InputSnapshot.identity`。

```python
def test_canonical_json_is_order_stable_but_list_order_sensitive(self) -> None:
    self.assertEqual(canonical_json_bytes({"b": 2, "a": [1, 2]}), canonical_json_bytes({"a": [1, 2], "b": 2}))
    self.assertNotEqual(semantic_hash({"a": [1, 2]}), semantic_hash({"a": [2, 1]}))

def test_generated_paths_reject_escape_and_absolute_ids(self) -> None:
    for value in ("../escape", "/absolute", "C:\\escape"):
        with self.subTest(value=value), self.assertRaises(ValueError):
            compile_paths(ROOT, value)
```

- [ ] **Step 2: Run RED on compute node**

Run `python3.11 -m unittest tests.test_p3_compiler_types -v` through `tssrun`。Expected: import failure for `paperops.compiler`。

- [ ] **Step 3: Implement immutable DTO and storage kernel**

Use frozen dataclasses and `to_dict()` methods returning JSON-compatible values. `semantic_hash` must return `sha256:<hex>` over canonical bytes. `atomic_write_json` must create a same-directory temp file, fsync, `os.replace`, and clean the temp on failure。

- [ ] **Step 4: Run GREEN and full related tests**

Run Task 1 test plus `tests.test_model_migration_staging` and `tests.test_model_state`。Expected: all pass。

- [ ] **Step 5: Commit**

Commit message: `compile生成物を正本と混同しないためP3の型と保存境界を追加`

### Task 2: Managed compile schemas and Manuscript planning extension

**Files:**

- Create: `template/_paperops/defaults/schemas/compile-bundle.schema.json`
- Create: `template/_paperops/defaults/schemas/section-plan.schema.json`
- Create: `template/_paperops/defaults/schemas/writer-packet.schema.json`
- Create: `template/_paperops/defaults/schemas/writer-patch.schema.json`
- Modify: `template/_paperops/defaults/schemas/manuscript-section.schema.json`
- Modify: `template/_paperops/defaults/schemas/manuscript-block.schema.json`
- Modify: `template/scripts/paperops_models.py`
- Test: `tests/test_p3_manuscript_contract.py`

**Interfaces:**

- Adds optional section `move_bindings[] = {move_id, role: primary|echo, reason}` while preserving `editorial_move_refs` compatibility projection。
- Adds block operation `add`; canonical typed operations become `keep/compress/move/merge/split/cut/rewrite/add`。
- Adds semantic findings `compile.move_binding_mismatch`, `compile.move_primary`, `compile.plan_approval`, `compile.dependency_coverage` without making empty starters invalid。
- Defines JSON schema version 1 for all generated DTOs; `additionalProperties: false` except versioned extensions。

- [ ] **Step 1: Write schema-first failing tests**

Cover valid/invalid move roles, duplicate primary placement, binding/ref mismatch, `add` acceptance, unknown generated fields, packet input object requiring identity/type/hash/relation, relative read/write paths, and starter compatibility。

```python
def test_move_bindings_are_additive_and_match_editorial_refs(self) -> None:
    section = valid_section()
    section["move_bindings"] = [{"move_id": "MOV-0001", "role": "primary", "reason": "principal result"}]
    section["editorial_move_refs"] = ["MOV-0001"]
    self.assertEqual(validate_document(SECTION_SCHEMA, section), [])
```

- [ ] **Step 2: Run RED**

Run `tests.test_p3_manuscript_contract` through compute node。Expected: missing schema files and rejected `move_bindings` / `add`。

- [ ] **Step 3: Add schemas and semantic validation**

Keep new section fields optional for downstream compatibility. Require them only in P3 compiler readiness, not ordinary P1-B schema validation. Keep existing checker phase and finding exit semantics。

- [ ] **Step 4: Run GREEN and P1-B regression**

Run Task 2 test, `tests.test_manuscript_model`, `tests.test_paperops_model_check`, `tests.test_pops_cli`。Expected: all pass and empty starters remain advisory-compatible。

- [ ] **Step 5: Commit**

Commit message: `全体moveをsection計画へ追跡するためP3 schemaを追加`

### Task 3: Safe checker queries and authority input snapshot

**Files:**

- Modify: `src/paperops/model_validation.py`
- Modify: `template/scripts/check-paperops-models.py`
- Create: `src/paperops/compiler/inputs.py`
- Create: `tests/test_p3_compile_inputs.py`

**Interfaces:**

- Produces `run_model_hash(root, model, object_id=None) -> ValidationResult` using the same bounded-output, no-shell runner。
- Produces a whitelisted read-only Manuscript compile-readiness query through the project-managed checker, so Task 5 does not import template scripts or duplicate `validate_manuscript_compile_readiness()`。
- Produces `load_compile_inputs(root, request) -> LoadedCompileInputs` with validated YAML documents, catalog object snapshots, authority snapshots, and source mode。
- Authoritative mode calls `plan_adoption` for Research, Editorial, Results hierarchy, Manuscript and rejects non-v2 / inconsistent journal state。
- Shadow mode overlays only the declared P2 candidate into an isolated temp project, validates it, and marks output non-applicable。

- [ ] **Step 1: Write authority and query RED tests**

Cover missing checker, valid object hash, compile-readiness target selection, malformed checker JSON, legacy/shadow/v2 modes, missing transaction, tampered target, model validation failure, and source-tree no-mutation. Build authoritative fixtures by using existing P2 diff/adopt helpers rather than hand-writing manifest state。

- [ ] **Step 2: Run RED**

Run `tests.test_p3_compile_inputs`。Expected: missing `run_model_hash` / `load_compile_inputs`。

- [ ] **Step 3: Implement generalized checker argv and input loader**

Refactor the safe runner to accept only enumerated `--print-hash`, `--object-id`, and Manuscript compile-readiness arguments. Never interpolate shell text. Load only paths registered by the validated model index, reject symlink/special files, and retain project-relative identities only。

- [ ] **Step 4: Run GREEN and safety regression**

Run Task 3 test, `tests.test_model_validation`, P2 transaction/rollback tests, and core model checker tests。

- [ ] **Step 5: Commit**

Commit message: `未承認modelをWriterへ流さないためcompile入力をauthority検証`

### Task 4: Contract overlay, TeX block, mirror, and terminology snapshots

**Files:**

- Create: `src/paperops/compiler/contracts.py`
- Create: `src/paperops/compiler/tex.py`
- Create: `src/paperops/compiler/privacy.py`
- Create: `tests/test_p3_compile_context.py`

**Interfaces:**

- Produces `resolve_section_contract(root, section_kind) -> ResolvedContract` with precedence managed default < project overlay < writing profile and an input hash per layer。
- Rejects unknown/destructive overlay operations; mappings merge recursively, ordered lists replace only when the overlay declares the complete list, and `null` deletion is unsupported。
- Produces `scan_manuscript(root) -> ManuscriptSnapshot` with full read paths/hashes, `% block:` order/content hashes, map.toml pairs, freshness facts, terminology rules, the existing shared/imported/curated BibTeX registries as `{identity,content_hash,sorted keys}`, legacy analysis-request `{id,status,identity,content_hash}` snapshots, and duplicate/missing findings。
- Produces reusable pure `parse_tex_bytes(identity, content)` and explicit typed-block binding APIs; typed `BLK-*` identity and raw `% block:` identity remain separate, and marker IDs accept the Manuscript schema's `[A-Za-z0-9:._-]+` set。
- Records exact per-block citation keys, `N of M` quantities, figure labels/references, predicted-result markers/AREQ refs/placeholders, and authoring-intent hits for later conservation checks, without placing raw TeX in generated global context。
- Produces a shared context-aware privacy predicate/redacted finding boundary for contract/profile, terminology, ledger, citation/figure inventories, and later Task 5 projections; public DOI/HTTPS/citation/software and project-relative identities remain allowed。
- Does not invoke `mirror-freshness-check --update` or mutate ledger。

- [ ] **Step 1: Write RED tests**

Cover default-only contract, additive overlay, profile override trace, null/unknown destructive input, duplicate `% block:`, reordered pair, one-language drift, `ja_tex_block_id` explicit binding, colon-bearing raw marker IDs, exact citation/quantity/figure/prediction/intent inventories, BibTeX key existence/duplicates without exposing raw entries, public DOI preservation, private absolute-path rejection in Writer-facing terminology, and safe/unique legacy analysis-request frontmatter capture without exposing its raw body。

- [ ] **Step 2: Run RED**

Run Task 4 test。Expected: missing modules。

- [ ] **Step 3: Implement deterministic resolver and scanner**

Parse TOML with `tomllib`, YAML with `yaml.safe_load`, TeX as UTF-8 text. Treat project-relative file identity separately from Writer-facing public material. Keep the full TeX content in workspace copy, not `global.json`。

- [ ] **Step 4: Run GREEN and mirror/contract regression**

Run Task 4 test plus section-contract, mirror-check, mirror-freshness, public-terms, and concept-term tests。

- [ ] **Step 5: Commit**

Commit message: `全体文脈と変更範囲を分けるためcontractとTeX snapshotを型付け`

### Task 5: Deterministic global context, section plans, and Writer packets

**Files:**

- Modify: `src/paperops/compiler/types.py`
- Modify: `template/_paperops/defaults/schemas/compile-bundle.schema.json`
- Modify: `template/_paperops/defaults/schemas/section-plan.schema.json`
- Modify: `template/_paperops/defaults/schemas/writer-packet.schema.json`
- Create: `src/paperops/compiler/materialize.py`
- Modify: `src/paperops/compiler/privacy.py`
- Create: `tests/test_p3_compile_materialize.py`
- Create: `tests/fixtures/p3/compiler/approved/**`

**Interfaces:**

- Produces `materialize_compile(inputs, contract_snapshot, manuscript_snapshot, request) -> CompileBundleCandidate`。
- Extends catalog `InputSnapshot` with an optional full canonical `content_hash` while retaining the authority/profile-aware semantic `hash`; materialized catalog inputs require both, and generated schemas remain closed。
- Propagates `LoadedCompileInputs.snapshot_hash` as a non-catalog `compile-snapshot` input into compile-ID material and every Writer packet, so checker/schema/approval-only input changes cannot reuse an earlier packet。
- Emits `global_context`, one `SectionPlan` per target, and one or more `WriterPacket` objects without writing files。
- Every packet input is exactly one catalog object snapshot or non-catalog content snapshot; all refs require dependency coverage, including the content hash of every analysis-request card used to authorize predicted material。
- Compile readiness requires selected story, move coverage, current section `editorial_choice` approval, current Research approvals/gates, non-stale dependencies, contract functions, and scope topology。
- Results/Discussion/Methods projections preserve the field families in the design spec; depth remains a diagnostic floor, never generation target。

- [ ] **Step 1: Build approved fixture and RED assertions**

Materialize complete Research, Editorial/Results, Manuscript records, model authority journals, contracts, JA/EN TeX, mirror map/ledger, terminology, and writing profile. Assert exact global story, rejected reasons, claim roles, move order, section plan, packet inputs, semantic/content hashes, compile snapshot dependency, read context, write scope, forbidden terms, and no raw TeX duplication in global context。

- [ ] **Step 2: Add one-mutation RED corpus**

Cover missing/rejected/stale approval, not-ready gate, dangling/wrong type, stale dependency, missing move primary, unbound contract, missing block marker, private value, predicted evidence without AREQ, unplanned topology, and an approval-only mutation that keeps the model semantic hash stable but changes object content hash, compile ID, and packet dependency hash。

- [ ] **Step 3: Run RED**

Run Task 5 test。Expected: missing materializer。

- [ ] **Step 4: Implement pure materializer**

Use explicit field maps by section kind. Return all stable findings; never synthesize thesis, approval, quantity denominator, scope, evidence, or public wording. If any error exists, return no successful plans/packets。

- [ ] **Step 5: Run GREEN and deterministic repeat test**

Assert two calls yield identical DTO dictionaries/hashes and input semantic mutation changes compile ID material. Run Research/Editorial/Manuscript model tests alongside Task 5。

- [ ] **Step 6: Commit**

Commit message: `論文全体の意味を局所Writerへ渡すためtyped compileを実装`

### Task 6: Atomic bundle materialization and alternative-story compare

**Files:**

- Create: `src/paperops/compiler/bundles.py`
- Create: `src/paperops/compiler/compare.py`
- Create: `tests/test_p3_compile_bundles.py`

**Interfaces:**

- Produces `prepare_bundle(root, request, refresh=False) -> CompileResult` and `compare_bundles(root, left_id, right_id) -> CompileComparison`。
- Writes successful bundle atomically to `.paperops/compile/<compile-id>/`; writes diagnostic failure report without partial success bundle。
- Reuses identical compile ID unless `--refresh`, and refresh must remain byte-identical for identical inputs。
- Comparison reports selected story, move order, claim roles, result order, section placement, visual obligations, target/scope changes; it never ranks candidates。

- [ ] **Step 1: Write RED tests**

Cover byte-identical repeat, failure no partial bundle, corrupted existing bundle, refresh, source mutation new ID, compare ordering and semantic delta, absolute/private redaction, and tracked-tree identity。

- [ ] **Step 2: Run RED**

Run Task 6 test。Expected: missing bundle APIs。

- [ ] **Step 3: Implement staging and comparison**

Materialize into a same-filesystem temporary sibling directory, fsync JSON files, validate hashes, then `os.replace`. `compare_bundles` loads only confined IDs and verified bundle schemas。

- [ ] **Step 4: Run GREEN and P2 staging regression**

Run Task 6 test plus model migration staging/catalog tests。

- [ ] **Step 5: Commit**

Commit message: `alternative storyを正本化せず比較できるようcompile bundleを永続化`

### Task 7: Public `pops compile` CLI

**Files:**

- Create: `src/paperops/cli/compile_commands.py`
- Modify: `src/paperops/cli/main.py`
- Create: `tests/test_pops_compile_cli.py`

**Interfaces:**

- Adds exactly `status`, `prepare`, `compare` under `pops compile` with syntax from the spec。
- Human and `--json` render the same `CompileResult` / `CompileComparison` domain object。
- Runs P2 incomplete-transaction recovery before reading authority state, but never adopts a model or invokes AI。

- [ ] **Step 1: Write parser/result RED tests**

Cover exact action names, invalid target/scope, non-project, authoritative blocker, shadow non-applicable marker, repeat/reuse/refresh, JSON shape/version, no traceback/absolute path, and tracked no-mutation。

- [ ] **Step 2: Run RED**

Run `tests.test_pops_compile_cli`。Expected: parser rejects `compile`。

- [ ] **Step 3: Implement CLI adapter**

Keep argparse construction in `compile_commands.py`; keep rendering free of filesystem reads. Exit 0 only without error findings, exit 1 for domain blockers, exit 2 for missing project/usage-level state。

- [ ] **Step 4: Run GREEN and existing CLI regression**

Run Task 7 test, `tests.test_pops_model_cli`, `tests.test_pops_cli`。

- [ ] **Step 5: Commit**

Commit message: `AIを起動せず全体文脈をcompileできるようCLI入口を追加`

### Task 8: Candidate workspace and scoped TeX patch

**Files:**

- Create: `src/paperops/compiler/writer.py`
- Create: `src/paperops/compiler/patches.py`
- Create: `tests/test_p3_writer_workspace.py`

**Interfaces:**

- Produces `start_writer_session(root, compile_id) -> WriterSessionResult`, `inspect_writer_session(root, session_id) -> WriterSessionResult`, `build_patch(root, session_id) -> WriterPatchResult`。
- Copies the full living `manuscript/` tree into the ignored workspace, records byte hash/mode for every file, and copies no `_paperops` private/raw state into Writer-facing files。
- Patch parser binds project-relative file plus `% block:` identity; it distinguishes add/remove/move/content change and rejects scope-outside changes, unplanned topology, special files, symlinks, and preamble/shared/bib changes without explicit scope。

- [ ] **Step 1: Write RED tests**

Cover full-manuscript readable copy, tracked no-mutation, block-only accepted edit, other-block/other-section/preamble rejection, current-model planned add/move acceptance, unplanned add as `replan_required`, duplicate marker, binary/symlink, and candidate workspace not confused with `submission/`。

- [ ] **Step 2: Run RED**

Run Task 8 test。Expected: missing writer/patch APIs。

- [ ] **Step 3: Implement session and scope diff**

Use random path-safe session ID because sessions are mutable. Store immutable base manifest and compile bundle hash. Do not use `git diff` as authority; compare recorded bytes and parsed block regions directly。

- [ ] **Step 4: Run GREEN and manuscript scanner regression**

Run Task 8 and Task 4 tests plus submission drift and TeX structure tests。

- [ ] **Step 5: Commit**

Commit message: `全体を読みつつ対象外を壊さないWriter workspaceを追加`

### Task 9: Conservation, mirror impact, privacy, and deterministic patch report

**Files:**

- Modify: `src/paperops/compiler/patches.py`
- Create: `src/paperops/compiler/conservation.py`
- Create: `tests/test_p3_writer_validation.py`

**Interfaces:**

- Produces `validate_patch(bundle, base, candidate, patch) -> tuple[CompileFinding, ...]`。
- Tracks claim/result/quantity/figure/citation/move disposition as `preserved/moved/removed` with an explicit model-authorized reason for removal。
- Reports JA/EN paired changes, single-language freshness drift, block order/duplicate/missing, terminology forbidden/internal values, predicted markers/AREQ, and private data。
- Never updates mirror ledger or changes candidate content。

- [ ] **Step 1: Write single-mutation RED matrix**

Cover unexplained claim/quantity/figure/citation/move loss separately, model-authorized cut, cross-block move, paired mirror, single-language drift warning, blind ledger update rejection, internal terminology, public DOI/software false-positive prevention, credential/path/raw review rejection, and stable report redaction。

- [ ] **Step 2: Run RED**

Run Task 9 test。Expected: conservation findings absent。

- [ ] **Step 3: Implement exact reference extraction and disposition validation**

Use TeX command/comment patterns already recognized by existing checkers; do not infer scientific equivalence from prose. Reuse privacy boundary helpers where safe and keep project-relative identities separate from public snippets。

- [ ] **Step 4: Run GREEN and checker equivalence set**

Run Task 9 plus mirror, quantity, citation, predicted-results, public-terms, authoring-intent, figure-reference, claim-evidence tests。

- [ ] **Step 5: Commit**

Commit message: `意味のある参照を黙って落とさないためWriter patchを保存検査`

### Task 10: Journaled TeX apply, recovery, and rollback

**Files:**

- Create: `src/paperops/compiler/write_transaction.py`
- Create: `tests/test_p3_write_transaction.py`

**Interfaces:**

- Produces `plan_write_apply`, `execute_write_apply`, `recover_incomplete_writes`, `plan_write_rollback`, `execute_write_rollback`。
- Journal states are `planned/materialized/validated/snapshotted/replacing/committed/rolled_back/conflict`。
- Transaction records compile ID, session ID, patch hash, authority snapshot, scope, human confirmation, target pre/post hashes, snapshot manifest, mirror impact。
- Only living TeX targets are replaced; model/workflow/mirror ledger stay byte-identical。

- [ ] **Step 1: Write apply/rollback RED tests**

Cover `--yes` equivalent confirmation, dry planning no mutation, base drift, candidate drift, scope recheck, shadow rejection, multi-file atomic apply, injected failure at every journal boundary, known-hash recovery, unknown manual edit conflict, corrupt/missing snapshot, latest/specific rollback, rollback repeat no-op, and post-apply human edit block。

- [ ] **Step 2: Run RED**

Run Task 10 test。Expected: missing transaction APIs。

- [ ] **Step 3: Implement conservative transaction**

Reuse P2 snapshot/path-hash primitives only after extracting generic read-only helpers; do not weaken P2 recovery. Copy candidate files to same-filesystem replacement paths before `os.replace`. Recovery restores only recognized pre/post hashes and otherwise records conflict。

- [ ] **Step 4: Run GREEN and P2 transaction regression**

Run Task 10 plus P2 adoption/rollback/staging tests。

- [ ] **Step 5: Commit**

Commit message: `人間編集を上書きせずTeXを反映できるようWriter適用をtransaction化`

### Task 11: Public `pops write` CLI and wheel distribution

**Files:**

- Create: `src/paperops/cli/write_commands.py`
- Modify: `src/paperops/cli/main.py`
- Create: `tests/test_pops_write_cli.py`
- Modify: `tests/test_p2_migration_fixtures.py` or create `tests/test_p3_distribution.py`

**Interfaces:**

- Adds exactly `start/status/check/diff/apply/rollback` under `pops write`。
- `apply` requires `--yes`; `start/status/check/diff` never mutate tracked files; rollback requires known transaction and conflict checks。
- Preflight calls P2 and P3 recovery; JSON/human share one domain result; no traceback/private/absolute output。
- Built wheel supports `pops compile` and `pops write` on copied scaffold using project-managed checker/contracts。

- [ ] **Step 1: Write CLI and wheel RED tests**

Cover exact parser surface, invalid IDs, non-project, lifecycle happy path, no-confirmation, shadow apply, scope error, base conflict, apply/rollback repeat, JSON shape, source-tree/wheel installation, and copied scaffold no package-boundary leak。

- [ ] **Step 2: Run RED**

Run Task 11 tests。Expected: parser rejects `write`。

- [ ] **Step 3: Implement CLI adapters and renderers**

Keep orchestration only in CLI; transaction/domain logic remains in compiler modules. Public messages use project-relative paths and stable finding codes。

- [ ] **Step 4: Run GREEN and broad CLI regression**

Run Task 11, compile CLI, model CLI, pops CLI, scaffold boundary tests。

- [ ] **Step 5: Commit**

Commit message: `候補TeXの確認と承認適用を一つのpops write入口へ集約`

### Task 12: Downstream skills, docs, migration, fixtures, and final regression

**Files:**

- Modify: `template/.agents/skills/compile-results-section/SKILL.md`
- Modify: `template/.agents/skills/compile-discussion-section/SKILL.md`
- Modify: `template/.agents/skills/compile-methods-section/SKILL.md`
- Modify: `template/.agents/skills/design-paper-storyline/SKILL.md`
- Modify: `template/.agents/skills/review-block-flow/SKILL.md`
- Modify matching `template/.claude/skills/**/SKILL.md` wrappers only if wrapper contract requires it
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/README.md`
- Modify: `.gitignore`
- Modify: `template/.gitignore`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli.md`
- Modify: `docs/current-specification.md`
- Modify: `docs/migrations/v0.md`
- Modify: `docs/skill-catalog.md`
- Modify: `docs/paperops2-disposition.md`
- Modify: `CHANGELOG.md`
- Modify: `_handoff/TODO.md` (ignored local ledger)
- Create: `tests/test_p3_documentation.py`
- Create: `tests/test_p3_end_to_end.py`

**Interfaces:**

- Documents compile/write commands, read-context/write-scope distinction, candidate direct TeX editing, global replan, semantic-vs-mechanical boundary, storage, approval, recovery, rollback, P4 handoff, and P7 legacy cutover deferral。
- Skills call deterministic CLI for routine work, allow candidate TeX direct iteration, and escalate semantic problems to block/section/global revision rather than widening scope silently。

- [ ] **Step 1: Write documentation/E2E RED tests**

Assert exact public commands and boundaries across root/downstream surfaces. E2E cases must cover approved authoritative compile, shadow compare, alternative story compare, block/section/manuscript session, no-mutation, scope violation, semantic conservation, single-language mirror drift, apply/rollback, existing gate equivalence, and built wheel。

- [ ] **Step 2: Run RED**

Run P3 documentation and E2E tests。Expected: missing docs/skill command references。

- [ ] **Step 3: Update all public interfaces and ignored paths**

Ignore `.paperops/compile/` and `.paperops/writer/` in root and scaffold. Preserve legacy skill names and wrappers. Add migration note explaining that P3 is opt-in, P2 model state is not auto-adopted, P4 model/workflow writer is not yet active, and human direct TeX editing remains valid。

- [ ] **Step 4: Run focused P3 matrix on compute node**

Run all `test_p3_*`, compile/write CLI, model validation, P2 transaction, manuscript model, mirror, section, block-flow, quantity, citation, figure, predicted, privacy, and distribution tests。

- [ ] **Step 5: Run full gates**

Run `make cli-smoke` and `make smoke` on SysB compute node. Run `git diff --check`; verify no generated compile/writer state is tracked, no absolute/private fixture value exists, and source-tree/wheel commands succeed。

- [ ] **Step 6: Review complete P3 range**

Use `review-template-regression`; fix every Critical/Important issue and rerun affected tests plus `make smoke`。

- [ ] **Step 7: Commit**

Commit message: `全体構成を見直せるままP3 Writer workflowを下流へ公開`

## Execution checkpoints

- Record RED/GREEN Slurm job IDs in `.superpowers/sdd/progress.md` after every task。
- Review each task for spec compliance before starting the next task。
- Do not combine multiple task commits or amend earlier approved task commits。
- After Task 12, keep local `main` for user review; do not push or release。
