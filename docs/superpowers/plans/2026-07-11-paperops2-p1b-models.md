# PaperOps 2 P1-B Implementation Plan

> **Execution:** Apply test-driven development task by task. After each task, run its focused tests, commit the coherent unit with a Japanese why-oriented message, and review the resulting commit range before continuing. Do not push or release.

**Goal:** Add Research, Manuscript, Issue, and Publication typed models; validate every model through a shared cross-model catalog; and provide deterministic approval and dependency-staleness diagnostics without changing legacy authority.

**Architecture:** Extend the P1-A registry with index-backed model entries and typed record sets. Keep schema validation in `paperops_schema.py`, put cross-model catalog/reference/approval/dependency logic in a new dependency-free `paperops_models.py`, and let `check-paperops-models.py` orchestrate phases. Research, Manuscript, and Issue use index + per-ID records; Publication remains a small aggregate document; Editorial and Results hierarchy keep their P1-A representation.

**Tech Stack:** Python 3.11 standard library, existing PyYAML runtime, PaperOps Schema Profile v1, `unittest`, Make, KUDPC `tssrun` for test execution.

**Design:** `docs/superpowers/specs/2026-07-11-paperops2-p1b-models-design.md`

---

## Task 1: Registry and index primitives

**Files:**

- Modify: `template/scripts/paperops_schema.py`
- Modify: `template/_paperops/defaults/schemas/registry.yml`
- Create: `template/_paperops/defaults/schemas/model-index.schema.json`
- Test: `tests/test_paperops_model_registry.py`
- Test: `tests/test_paperops_schema.py`

### Step 1: Write failing registry tests

Cover:

- six exact registry entries: Research, Editorial, Results hierarchy, Manuscript, Issue, Publication;
- aggregate entries remain backward-compatible;
- index entries require `document_kind: index`, `record_sets`, safe `path_prefix`, record schema file, ID pattern, and `dependency-v1`;
- missing/unknown record set fields and escaping schema/path values fail as `registry.*` definition errors;
- registry schema files cannot escape `_paperops/defaults/schemas/` through symlinks.

Run on a compute node:

```sh
python3.11 -m unittest tests.test_paperops_model_registry tests.test_paperops_schema -v
```

Expected: FAIL because `RegistryEntry` has no index/record-set contract.

### Step 2: Implement registry dataclasses and loader validation

Add immutable `RecordSetEntry`; extend `RegistryEntry` with `document_kind`, `record_sets`, record-level hash exclusions, and `dependency_profile`. Keep aggregate P1-A fields valid. Resolve schema and path prefix without project-root escape, validate regex definitions eagerly, and reject unknown registry keys needed to avoid silent typo acceptance.

### Step 3: Add shared index schema and six-entry registry

The generic index schema validates only the common envelope. Model-specific allowed record types are enforced by registry/catalog validation so the same managed schema can be reused without unsupported JSON Schema conditionals.

### Step 4: Run focused tests and commit

Expected: PASS. Commit the registry kernel as one unit.

## Task 2: Index discovery, record loading, and canonical object hash

**Files:**

- Create: `template/scripts/paperops_models.py`
- Modify: `template/scripts/check-paperops-models.py`
- Create: `tests/test_paperops_model_catalog.py`
- Modify: `tests/test_paperops_model_check.py`

### Step 1: Write failing catalog tests

Cover safe index row resolution, record schema selection, row/record ID-type-revision-hash agreement, global duplicate IDs, missing records, orphan records, unreadable records, path escape through POSIX/Windows spelling and symlinks, and schema-failed records being excluded from the catalog. Cover Editorial story/move/visual and Results item virtual objects with object-level hash and no fabricated revision.

Use temporary project roots and minimal test schemas. Assert exact finding code and JSON Pointer, not only exit status.

### Step 2: Implement catalog types and loading

Create typed `ModelDocument`, `RecordDocument`, `ObjectCatalog`, and catalog-building functions. Reuse `load_document`, `validate_document_version`, `validate_schema`, and `semantic_hash`. Never fall back to legacy cards when an index/record is malformed.

### Step 3: Extend checker orchestration

Load aggregate and index-backed models through one orchestration path. Preserve P1-A `--document` / `--results-document` fixture behavior. Add `--object-id` for canonical object hash and make output conditional on all required validation succeeding.

### Step 4: Run focused tests and commit

```sh
python3.11 -m unittest tests.test_paperops_model_catalog tests.test_paperops_model_check -v
```

Expected: PASS.

## Task 3: Research Model schemas and semantics

**Files:**

- Create: `template/_paperops/defaults/schemas/research-index.schema.json`
- Create: `template/_paperops/defaults/schemas/research-claim.schema.json`
- Create: `template/_paperops/defaults/schemas/research-result.schema.json`
- Create: `template/_paperops/defaults/schemas/research-figure.schema.json`
- Create: `template/_paperops/defaults/schemas/research-source.schema.json`
- Create: `template/_paperops/defaults/schemas/research-gate.schema.json`
- Create: `template/_paperops/model/research/index.yml`
- Modify: `template/scripts/paperops_models.py`
- Create: `tests/test_research_model.py`

### Step 1: Write schema and semantic tests first

Test every legacy card field family from claim/result/figure/source/scientific-gate templates, exact status enums, ID patterns, extension boundary, quantity contracts, approval envelope, and ready-to-write rules. Include one complete approved claim graph and focused invalid records.

### Step 2: Add schemas and empty starter index

Use shared `$defs` copied explicitly into each file where necessary; cross-file `$ref` remains prohibited. Unknown fields fail. Metadata timestamps are excluded from semantic hash through registry pointers; local/raw path fields are absent.

### Step 3: Implement Research semantics

Validate gate/claim pairing, current scientific approval, ready-to-write prerequisites, quantity IDs, and public provenance constraints. Keep validation history separate from approvals.

### Step 4: Run tests and commit

```sh
python3.11 -m unittest tests.test_research_model -v
```

## Task 4: Manuscript Model schemas and semantics

**Files:**

- Create: `template/_paperops/defaults/schemas/manuscript-index.schema.json`
- Create: `template/_paperops/defaults/schemas/manuscript-section.schema.json`
- Create: `template/_paperops/defaults/schemas/manuscript-block.schema.json`
- Create: `template/_paperops/model/manuscript/index.yml`
- Modify: `template/scripts/paperops_models.py`
- Create: `tests/test_manuscript_model.py`

### Step 1: Write failing tests

Cover all section kinds, ordered block IDs, contiguous positions, section/block ownership, JA/EN identity fields, Editorial move refs, Research refs, compile provenance, `dependency_hash`, `last_verified_dependency_hash`, operations, allowed operations, and forbidden scope expansion.

Assert that compiled blocks separately diagnose unapproved claims, non-writable gates, dangling refs, and stale dependencies.

### Step 2: Implement schemas and starter

Keep prose and TeX content out of the model. Store IDs and compile facts only. Empty starter index is valid in advisory mode.

### Step 3: Implement manuscript semantics

Validate block ordering, section membership, compiled-from completeness, approved claim and ready gate requirements, and current dependency state. Do not duplicate existing TeX mirror checker logic.

### Step 4: Run tests and commit

```sh
python3.11 -m unittest tests.test_manuscript_model -v
```

## Task 5: Issue Model schemas and closure semantics

**Files:**

- Create: `template/_paperops/defaults/schemas/issue-index.schema.json`
- Create: `template/_paperops/defaults/schemas/issue-feedback.schema.json`
- Create: `template/_paperops/defaults/schemas/issue-analysis-request.schema.json`
- Create: `template/_paperops/defaults/schemas/issue-writing-request.schema.json`
- Create: `template/_paperops/defaults/schemas/issue-response.schema.json`
- Create: `template/_paperops/defaults/schemas/issue-review-round.schema.json`
- Create: `template/_paperops/model/issues/index.yml`
- Modify: `template/scripts/paperops_models.py`
- Create: `tests/test_issue_model.py`

### Step 1: Write failing tests

Cover shared source/severity/route/target/confidentiality/closure fields and every typed payload. Preserve existing analysis request lifecycle, prediction/replacement/runops/provenance/reconciliation, writing constraints, response closure audit, and review-round delegation/integration decisions.

Test that raw reviewer text and absolute paths are rejected, `executed` requires output refs, `reconciled` requires reconciliation/signoff, and `closed` response cannot depend on open analysis/human decision.

### Step 2: Add schemas, starter, and semantics

Use public summaries and opaque local-reference IDs only. Do not store confidential raw text. Emit `semantic.predicted_unresolved` independently from closure errors.

### Step 3: Run tests and commit

```sh
python3.11 -m unittest tests.test_issue_model -v
```

## Task 6: Publication Model and immutable-round contract

**Files:**

- Create: `template/_paperops/defaults/schemas/publication-model.schema.json`
- Create: `template/_paperops/model/publication/publication-model.yml`
- Modify: `template/scripts/paperops_models.py`
- Create: `tests/test_publication_model.py`

### Step 1: Write failing tests

Cover separate authoring/candidate/round axes, venue requirements, current round resolution, unique round/snapshot paths, required source commit/gate/artifact/snapshot dependency data, approval binding, and submitted-or-later immutable marker.

Test publication rejection for predicted/unreconciled request, unapproved claim, stale block, missing response, and mutable submitted round. Confirm living manuscript state remains independent.

### Step 2: Implement schema, starter, and semantics

The starter has no fabricated submitted round. It may contain an empty current candidate. P1-B validates the immutability contract but does not create or freeze filesystem snapshots.

### Step 3: Run tests and commit

```sh
python3.11 -m unittest tests.test_publication_model -v
```

## Task 7: Cross-model references, approvals, and dependency-v1

**Files:**

- Modify: `template/scripts/paperops_models.py`
- Modify: `template/scripts/paperops_editorial.py`
- Modify: `template/scripts/check-paperops-models.py`
- Modify: `template/_paperops/defaults/schemas/registry.yml`
- Create: `tests/test_cross_model_validation.py`
- Create: `tests/test_dependency_hash.py`
- Modify: `tests/test_editorial_model_semantics.py`

### Step 1: Write failing graph tests

Build a complete six-document graph and mutate one property per case. Assert exact distinct codes for duplicate, dangling, wrong type, cardinality, missing/stale approval, stale revision, stale hash, dependency cycle, and unresolved predicted publication input.

Test stable dependency hash under YAML/mapping/dependency ordering and timestamp-only changes; test changes for target semantic hash, revision, relation, addition, and removal.

### Step 2: Implement reference contracts

Define field-to-target contracts as versioned managed metadata loaded from the registry or a companion constant validated against registered record types. Convert P1-A deferred CLM/FIG refs into real catalog resolution when Research is loaded. Preserve explicit Results document binding.

### Step 3: Implement dependency-v1

Resolve all targets, sort unordered dependency entries, serialize with semantic-v1 rules, reject cycles, compare expected and last-verified hashes, and add `--print-dependency-hash OBJECT_ID`.

### Step 4: Add phases and CLI guards

Support `approvals` and `dependencies` phases. `all` orders schema → references → semantics → approvals → dependencies → hash and suppresses unsafe secondary findings. `--print-*` returns only after all prerequisites pass.

### Step 5: Run tests and commit

```sh
python3.11 -m unittest tests.test_cross_model_validation tests.test_dependency_hash tests.test_editorial_model_semantics tests.test_paperops_model_check -v
```

## Task 8: Full-model fixtures and invalid corpus

**Files:**

- Modify: `tests/fixtures/editorial/mechanism-led/**`
- Modify: `tests/fixtures/editorial/boundary-led/**`
- Modify: `tests/fixtures/editorial/negative-result-led/**`
- Create: `tests/fixtures/models/invalid/**`
- Modify: `tests/test_editorial_fixtures.py`
- Create: `tests/test_p1b_fixtures.py`

### Step 1: Write fixture contract tests

Require every valid case to contain all model files and required record families, use only synthetic/public-safe text, pass strict all-phase validation, and have stable canonical/dependency hashes.

Require each invalid fixture to be a single documented mutation with exact expected finding codes. Ensure no private paths, credentials, raw review text, unpublished data, or generated output enters fixtures.

### Step 2: Expand the three valid fixtures

Use real expected hash values generated only after the semantic documents validate. Keep IDs distinct and cross-model edges meaningful for each story type.

### Step 3: Add invalid corpus and run tests

```sh
python3.11 -m unittest tests.test_editorial_fixtures tests.test_p1b_fixtures -v
```

### Step 4: Commit fixtures separately

This commit is the behavioral acceptance corpus and should not mix documentation changes.

## Task 9: Init/update boundaries, migration inventory, and documentation

**Files:**

- Modify: `src/paperops/cli/constants.py`
- Modify: `src/paperops/cli/scaffold.py`
- Modify: `src/paperops/cli/migrations.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli.md`
- Modify: `docs/migrations/v0.md`
- Modify: `docs/current-specification.md`
- Modify: `docs/skill-catalog.md`
- Modify: `docs/paperops2-disposition.md`
- Modify: `template/README.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/_paperops/model/README.md` or create it if absent
- Modify: `CHANGELOG.md`
- Modify: `_handoff/TODO.md` (ignored local ledger)
- Create: `tests/test_p1b_documentation.py`
- Modify: `tests/test_pops_cli.py`

### Step 1: Write failing boundary/documentation tests

Require managed schemas/scripts to be update-managed; require project model indexes/records to be init-only and never overwritten. Require exact six-model docs, legacy-authoritative warning, P2/P3/P4 deferrals, `M0-0005` guide-only migration, and field-disposition inventory for every legacy template field family.

### Step 2: Register starter and managed files

New init copies empty indexes/publication starter. Existing updates only add managed schemas/scripts. Do not auto-create or overwrite project-owned model state. Register `M0-0005` without filesystem mutation.

### Step 3: Update user interfaces and migration note

Document the per-ID layout, checker phases, hash commands, authority boundary, legacy compatibility, manual adoption order, and rollback/non-deletion rule. Add migration note because `template/AGENTS.md`, `template/CLAUDE.md`, `template/scripts/`, and `_paperops/defaults/` are user-facing interfaces.

### Step 4: Update ledgers

Mark P1-B only after strict fixtures and smoke pass. Do not mark P2 onward complete. Add the user-visible change to `CHANGELOG.md`; update the ignored `_handoff/TODO.md` locally.

### Step 5: Run focused tests and commit

```sh
python3.11 -m unittest tests.test_p1b_documentation tests.test_pops_cli -v
```

## Final verification and review

1. Run all P1-focused tests on a compute node.
2. Run `make smoke` on a compute node because `template/` and user interfaces changed.
3. Run `git diff --check`, inspect `git status`, and verify no generated files are tracked.
4. Review the complete P1-B range against the design acceptance conditions and fix every Critical/Important issue.
5. Re-run focused tests and `make smoke` after final fixes.
6. Append task/review/verification evidence to `.superpowers/sdd/progress.md`.
7. Stop before push/release and continue to P2 locally.

Suggested compute-node command:

```sh
tssrun -p gr20001b -t 0:30:0 --rsc p=1:t=4:c=4 bash -lc '
  cd /LARGE1/gr20001/b36291/Github/paperops &&
  python3.11 -m unittest \
    tests.test_paperops_model_registry \
    tests.test_paperops_model_catalog \
    tests.test_research_model \
    tests.test_manuscript_model \
    tests.test_issue_model \
    tests.test_publication_model \
    tests.test_cross_model_validation \
    tests.test_dependency_hash \
    tests.test_p1b_fixtures \
    tests.test_p1b_documentation -v &&
  make smoke
'
```
