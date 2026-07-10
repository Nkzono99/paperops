# Typed Results Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 複数の Results item を一意 ID と明示的な順序で保持し、旧 Markdown の複数 item も情報を上書きせず検査できるようにする。

**Architecture:** 新規 scaffold は project-owned の `_paperops/model/editorial/results-hierarchy.yml` を Results hierarchy の正本にし、managed JSON Schema を `_paperops/defaults/schemas/` に置く。`section-contract-check` は typed model を優先し、存在しない既存 project だけ旧 `_paperops/notes/views/storyline.md` を互換読み取りする。typed model の導入は guide-only migration とし、旧 project state を自動上書きしない。

**Tech Stack:** Python 3.11+、標準 `unittest`、PyYAML（既存依存、JSON fallback あり）、JSON Schema document、Make

## Global Constraints

- ルート層は template governance、`template/` 層は下流 scaffold として分ける。
- `_paperops/model/editorial/results-hierarchy.yml` は project-owned state であり、managed update 対象にしない。
- `_paperops/defaults/schemas/results-hierarchy.schema.json` は paperops-managed default として更新対象にする。
- 旧 Markdown は互換期間中に読み取るが、typed file が存在する場合は fallback しない。
- starter の placeholder は advisory、`--strict` では error にする。
- ユーザー影響を `CHANGELOG.md` と `docs/migrations/v0.md` に記録する。
- `template/`、script、skill の変更後は `make smoke` を計算ノードで実行する。
- テストは login node で直接実行せず、`tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2` から一つの controller process として実行する。

---

### Task 1: 旧 Markdown の上書きバグを再現して修正する

**Files:**

- Modify: `tests/test_section_contract_check.py`
- Modify: `template/scripts/check-section-contracts.py`

**Interfaces:**

- Consumes: `## Results hierarchy` 内の連続した Markdown bullet group
- Produces: `extract_legacy_results_items(body: str) -> list[tuple[str, dict[str, str]]]`

- [ ] **Step 1: 一項目目の不足が二項目目で上書きされる failing test を追加する**

```python
def test_strict_fails_when_any_legacy_results_item_is_incomplete(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_text(
            root / "_paperops" / "notes" / "views" / "storyline.md",
            """
                # Storyline

                ## Results hierarchy

                - reader question 1: What changes in the baseline?
                - one-sentence answer:
                - quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
                - figure / table role: Figure 2 shows the work budget.
                - baseline / comparator rationale: The control isolates retained charge.
                - consequence: The next item tests coupling.
                - reader question 2: Does the criterion survive coupling?
                - one-sentence answer: It survives only inside the stated boundary.
                - quantitative evidence and unit of analysis: 8 of 16 trajectories, per candidate.
                - figure / table role: Figure 3 shows the boundary.
                - baseline / comparator rationale: The coupled case tests the omitted process.
                - consequence: The Discussion interprets the boundary.

                ## Discussion functions

                - principal_finding: Baseline charging changes the work budget.
                - mechanism_warrant: Retained charge changes the force balance.
                - prior_work_delta: This separates local control from ambient estimates.
                - alternative_or_boundary: Coupled illumination is outside this control.
                - implication: The control defines a lower-complexity reference.
                - decisive_next_test: Add coupled illumination and reuse the criterion.

                ## Methods definition registry

                | item | definition location | manuscript block | status |
                | --- | --- | --- | --- |
                | estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | locked |
                | comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | locked |
                | decision_criteria | Methods, paragraph 4 | methods.criteria.01 | locked |
                | verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | locked |
            """,
        )
        result = run_python_script(SCRIPT, "--root", root, "--strict")

    self.assertEqual(result.returncode, 1)
    self.assertIn("Results hierarchy item `1`", result.stdout)
    self.assertIn("one-sentence answer", result.stdout)
```

- [ ] **Step 2: failing test を計算ノードで実行して RED を確認する**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_section_contract_check.SectionContractCheckTest.test_strict_fails_when_any_legacy_results_item_is_incomplete -v'
```

Expected: assertion failure。現行 parser は後の bullet で辞書値を上書きするため checker が成功してしまう。

- [ ] **Step 3: bullet group を item ごとに保持する parser を実装する**

```python
def extract_legacy_results_items(body: str) -> list[tuple[str, dict[str, str]]]:
    items: list[tuple[str, dict[str, str]]] = []
    current_label = "1"
    current_values: dict[str, str] | None = None
    pattern = re.compile(r"^[ \t]*-[ \t]*([^:]+):[ \t]*(.*)$", re.MULTILINE)
    for match in pattern.finditer(body):
        raw_key = match.group(1).strip()
        key = normalize_key(raw_key)
        if key == "reader_question":
            if current_values is not None:
                items.append((current_label, current_values))
            suffix = re.search(r"(\d+)\s*$", raw_key)
            current_label = suffix.group(1) if suffix else str(len(items) + 1)
            current_values = {}
        elif current_values is None:
            current_values = {}
        current_values[key] = match.group(2).strip()
    if current_values is not None:
        items.append((current_label, current_values))
    return items
```

`check_results_hierarchy` は返された全 item に `REQUIRED_RESULTS_FIELDS` を適用し、message に item label を含める。

- [ ] **Step 4: 対象 test と既存 section-contract tests を GREEN にする**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_section_contract_check -v'
```

Expected: `OK`。

- [ ] **Step 5: bugfix をコミットする**

```sh
git add tests/test_section_contract_check.py template/scripts/check-section-contracts.py
git commit -m "複数のResults項目を上書きせず検査するため"
```

---

### Task 2: typed Results hierarchy と参照整合を実装する

**Files:**

- Create: `template/_paperops/defaults/schemas/results-hierarchy.schema.json`
- Create: `template/_paperops/model/editorial/results-hierarchy.yml`
- Modify: `tests/test_section_contract_check.py`
- Modify: `tests/test_storyline_layer.py`
- Modify: `template/scripts/check-section-contracts.py`

**Interfaces:**

- Consumes: `_paperops/model/editorial/results-hierarchy.yml`
- Produces: `check_typed_results_hierarchy(rel_path: str, data: dict[str, Any], strict: bool) -> list[Finding]`
- Produces: ordered `items[]` with `RHI-*` IDs and `next_item_id`

- [ ] **Step 1: typed file を優先する failing tests を追加する**

```python
import json


COMPLETE_DISCUSSION_AND_METHODS = """
## Discussion functions

- principal_finding: Baseline charging changes the work budget.
- mechanism_warrant: Retained charge changes the force balance.
- prior_work_delta: This separates local control from ambient estimates.
- alternative_or_boundary: Coupled illumination is outside this control.
- implication: The control defines a lower-complexity reference.
- decisive_next_test: Add coupled illumination and reuse the criterion.

## Methods definition registry

| item | definition location | manuscript block | status |
| --- | --- | --- | --- |
| estimand_and_unit_of_analysis | Methods, paragraph 2 | methods.estimand.01 | locked |
| comparison_or_baseline | Methods, paragraph 3 | methods.baseline.01 | locked |
| decision_criteria | Methods, paragraph 4 | methods.criteria.01 | locked |
| verification_or_convergence | Methods, paragraph 5 | methods.verification.01 | locked |
"""

COMPLETE_LEGACY_RESULTS = """
## Results hierarchy

- reader question 1: What changes in the baseline?
- one-sentence answer: The work budget changes under the stated control.
- quantitative evidence and unit of analysis: 12 of 16 trajectories, per candidate.
- figure / table role: Figure 2 shows the work budget.
- baseline / comparator rationale: The control isolates retained charge.
- consequence: The next item tests coupling.
"""


def typed_result_item(item_id: str, next_item_id: str) -> dict[str, str]:
    return {
        "id": item_id,
        "reader_question": f"Reader question for {item_id}",
        "answer": f"Answer for {item_id}",
        "quantitative_evidence_and_unit_of_analysis": "12 of 16 trajectories, per candidate.",
        "figure_table_role": f"Figure for {item_id}",
        "baseline_comparator_rationale": "The control isolates the tested process.",
        "consequence": f"Consequence for {item_id}",
        "next_item_id": next_item_id,
    }


def write_typed_results(root: Path, items: list[dict[str, str]]) -> None:
    write_text(
        root / "_paperops" / "model" / "editorial" / "results-hierarchy.yml",
        json.dumps({"schema_version": 1, "items": items}, ensure_ascii=False, indent=2),
    )


def test_strict_passes_with_three_typed_results_items(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_text(
            root / "_paperops" / "notes" / "views" / "storyline.md",
            "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
        )
        write_typed_results(
            root,
            [
                typed_result_item("RHI-0001", "RHI-0002"),
                typed_result_item("RHI-0002", "RHI-0003"),
                typed_result_item("RHI-0003", ""),
            ],
        )
        result = run_python_script(SCRIPT, "--root", root, "--strict")

    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

def test_strict_fails_on_duplicate_typed_results_item_id(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_text(
            root / "_paperops" / "notes" / "views" / "storyline.md",
            "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
        )
        write_typed_results(
            root,
            [
                typed_result_item("RHI-0001", "RHI-0001"),
                typed_result_item("RHI-0001", ""),
            ],
        )
        result = run_python_script(SCRIPT, "--root", root, "--strict")

    self.assertEqual(result.returncode, 1)
    self.assertIn("duplicate Results hierarchy item id `RHI-0001`", result.stdout)

def test_strict_fails_on_broken_typed_results_chain(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_text(
            root / "_paperops" / "notes" / "views" / "storyline.md",
            "# Storyline\n\n" + COMPLETE_DISCUSSION_AND_METHODS,
        )
        write_typed_results(
            root,
            [
                typed_result_item("RHI-0001", "RHI-9999"),
                typed_result_item("RHI-0002", ""),
            ],
        )
        result = run_python_script(SCRIPT, "--root", root, "--strict")

    self.assertEqual(result.returncode, 1)
    self.assertIn("next_item_id `RHI-9999`", result.stdout)

def test_typed_results_hierarchy_does_not_fall_back_to_complete_legacy_view(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_text(
            root / "_paperops" / "notes" / "views" / "storyline.md",
            "# Storyline\n\n" + COMPLETE_LEGACY_RESULTS + COMPLETE_DISCUSSION_AND_METHODS,
        )
        item = typed_result_item("RHI-0001", "")
        item["answer"] = "未記入"
        write_typed_results(root, [item])
        result = run_python_script(SCRIPT, "--root", root, "--strict")

    self.assertEqual(result.returncode, 1)
    self.assertIn("RHI-0001", result.stdout)
    self.assertIn("answer", result.stdout)
```

`tests/test_storyline_layer.py` では schema と starter model の存在、および `next_item_id` を検査する。

- [ ] **Step 2: typed tests を実行して RED を確認する**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_section_contract_check tests.test_storyline_layer -v'
```

Expected: typed file が未実装のため失敗。

- [ ] **Step 3: managed JSON Schema を追加する**

Schema は `schema_version` と非空の `items` を要求し、各 item は次を持つ。

```json
{
  "id": "RHI-0001",
  "reader_question": "未記入",
  "answer": "未記入",
  "quantitative_evidence_and_unit_of_analysis": "未記入",
  "figure_table_role": "未記入",
  "baseline_comparator_rationale": "未記入",
  "consequence": "未記入",
  "next_item_id": ""
}
```

`additionalProperties` は schema root と item の両方で `false` にする。

- [ ] **Step 4: starter typed model を追加する**

```yaml
schema_version: 1
items:
  - id: RHI-0001
    reader_question: 未記入
    answer: 未記入
    quantitative_evidence_and_unit_of_analysis: 未記入
    figure_table_role: 未記入
    baseline_comparator_rationale: 未記入
    consequence: 未記入
    next_item_id: ""
```

- [ ] **Step 5: typed checker を実装する**

`resolve_results_hierarchy_path(root)` は `_paperops/model/editorial/results-hierarchy.yml` を返す。file が存在する場合は `paperops_checks.load_mapping` で読み、次を検査する。

1. `schema_version == 1`
2. `items` が非空 list
3. item が mapping
4. `id` が placeholder でなく一意
5. 全 required field が placeholder でない
6. 非終端 item の `next_item_id` が配列上の次 item ID と一致
7. 終端 item の `next_item_id` が空

typed file が存在しない場合だけ Task 1 の legacy parser へ fallback する。

- [ ] **Step 6: typed tests と既存 tests を GREEN にする**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_section_contract_check tests.test_storyline_layer -v'
```

Expected: `OK`。

- [ ] **Step 7: typed hierarchy をコミットする**

```sh
git add template/_paperops/defaults/schemas/results-hierarchy.schema.json \
  template/_paperops/model/editorial/results-hierarchy.yml \
  template/scripts/check-section-contracts.py \
  tests/test_section_contract_check.py tests/test_storyline_layer.py
git commit -m "Results階層を一意ID付きの型で管理するため"
```

---

### Task 3: managed distribution と guide-only migration を接続する

**Files:**

- Modify: `src/paperops/cli/constants.py`
- Modify: `src/paperops/cli/migrations.py`
- Modify: `src/paperops/cli/output.py`
- Modify: `tests/test_pops_cli.py`
- Modify: `docs/migrations/v0.md`
- Modify: `docs/upgrade-policy.md`

**Interfaces:**

- Consumes: managed `_paperops/defaults/schemas/*`
- Produces: `M0-0003` guide-only migration metadata

- [ ] **Step 1: managed schema と M0-0003 の failing tests を追加する**

```python
def test_update_paperops_can_add_managed_schema_defaults(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "paper-demo"
        run_cli(["init", str(target)])
        schema = target / "_paperops" / "defaults" / "schemas" / "results-hierarchy.schema.json"
        schema.unlink()

        code, out, err = run_cli(
            [
                "update-paperops",
                "--dry-run",
                "--only",
                "_paperops/defaults/schemas/",
                str(target),
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertIn(
            "+ _paperops/defaults/schemas/results-hierarchy.schema.json [schema]",
            out,
        )

        code, _out, err = run_cli(
            [
                "update-paperops",
                "--apply",
                "--only",
                "_paperops/defaults/schemas/",
                str(target),
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(schema.is_file())

def test_migrate_lists_typed_results_hierarchy_guide(self) -> None:
    code, out, err = run_cli(["migrate", "list"])
    self.assertEqual(code, 0, err)
    self.assertIn("M0-0003", out)
    code, out, err = run_cli(["migrate", "show", "M0-0003"])
    self.assertEqual(code, 0, err)
    self.assertIn("results-hierarchy.yml", out)
    self.assertIn("legacy", out.lower())
```

- [ ] **Step 2: tests を実行して RED を確認する**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_pops_cli -v'
```

Expected: schema managed pattern と M0-0003 がないため失敗。

- [ ] **Step 3: schema managed pattern と output label を追加する**

`MANAGED_UPDATE_PATTERNS` に `_paperops/defaults/schemas/*` を追加する。output surface は `schema` と表示する。

- [ ] **Step 4: M0-0003 を guide-only migration として登録する**

```python
TYPED_RESULTS_HIERARCHY_MIGRATION = Migration(
    migration_id="M0-0003",
    title="Adopt the typed Results hierarchy model",
    checkpoint="v0 checkpoint for typed editorial state",
    summary=(
        "Introduces project-owned _paperops/model/editorial/results-hierarchy.yml "
        "while retaining the legacy Markdown reader for existing projects."
    ),
    moves=(),
    notes=(
        "New projects receive the typed starter model from pops init.",
        "Existing projects may keep the legacy storyline.md Results hierarchy during the compatibility checkpoint.",
        "Adopt the typed file manually from the starter schema, then run make section-contract-check.",
    ),
)
```

`registered_migrations()` に M0-0003 を追加する。

- [ ] **Step 5: migration docs を更新する**

`docs/migrations/v0.md` に、旧 Markdown を削除する前に typed file を作り、strict checker を通し、`pops update-paperops --apply --only _paperops/defaults/schemas/` で managed schema を受け取る手順を書く。

- [ ] **Step 6: CLI tests を GREEN にする**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_pops_cli -v'
```

Expected: `OK`。

- [ ] **Step 7: distribution と migration をコミットする**

```sh
git add src/paperops/cli/constants.py src/paperops/cli/migrations.py \
  src/paperops/cli/output.py tests/test_pops_cli.py \
  docs/migrations/v0.md docs/upgrade-policy.md
git commit -m "既存論文を壊さず型付きResults階層へ移れるようにするため"
```

---

### Task 4: starter interface、skills、docs、変更履歴を更新する

**Files:**

- Modify: `template/_paperops/notes/views/storyline.md`
- Modify: `template/_paperops/defaults/contracts/storyline.yml`
- Modify: `template/.agents/skills/design-paper-storyline/SKILL.md`
- Modify: `template/.agents/skills/compile-results-section/SKILL.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/README.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/current-specification.md`
- Modify: `docs/skill-catalog.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_storyline_layer.py`
- Modify: `tests/test_root_guidance.py`

**Interfaces:**

- Consumes: typed Results hierarchy path and legacy fallback policy
- Produces: downstream user guidance and migration note

- [ ] **Step 1: docs surface の failing assertions を追加する**

`tests/test_storyline_layer.py` と `tests/test_root_guidance.py` で次を要求する。

```python
self.assertIn("_paperops/model/editorial/results-hierarchy.yml", combined)
self.assertIn("typed Results hierarchy", combined)
self.assertIn("legacy Markdown", combined)
```

- [ ] **Step 2: docs tests を実行して RED を確認する**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_storyline_layer tests.test_root_guidance -v'
```

Expected: typed path の説明がないため失敗。

- [ ] **Step 3: storyline view と contract の正本境界を更新する**

`storyline.md` の `authoritative_for` から `results_hierarchy` を外し、typed path を source として追加する。`## Results hierarchy` は typed source への短い案内にし、値を複製しない。

- [ ] **Step 4: skills と downstream interface を更新する**

`design-paper-storyline` と `compile-results-section` は typed file を必須入力として扱い、item ID、`next_item_id`、strict checker を明記する。既存 project では migration 完了まで legacy Markdown fallback を許す。

- [ ] **Step 5: root docs と CHANGELOG を更新する**

Architecture には typed Editorial state と project-owned / managed schema の境界を書く。Current specification index、skill catalog、root/downstream README を更新する。CHANGELOG には既存下流が schema default を更新し、typed file は opt-in で作る migration note を書く。

- [ ] **Step 6: docs tests を GREEN にする**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_storyline_layer tests.test_root_guidance -v'
```

Expected: `OK`。

- [ ] **Step 7: interface/docs をコミットする**

```sh
git add template/_paperops/notes/views/storyline.md \
  template/_paperops/defaults/contracts/storyline.yml \
  template/.agents/skills/design-paper-storyline/SKILL.md \
  template/.agents/skills/compile-results-section/SKILL.md \
  template/AGENTS.md template/CLAUDE.md template/README.md README.md \
  docs/architecture.md docs/current-specification.md docs/skill-catalog.md \
  CHANGELOG.md tests/test_storyline_layer.py tests/test_root_guidance.py
git commit -m "Results階層の新しい正本を下流利用者へ明示するため"
```

---

### Task 5: 回帰確認と公開可能な作業単位の検証

**Files:**

- Review: all files changed by Tasks 1-4

**Interfaces:**

- Consumes: complete typed hierarchy slice
- Produces: fresh test evidence and regression review

- [ ] **Step 1: 対象 tests を計算ノードで実行する**

```sh
tssrun -p gr20001b -t 0:20:0 --rsc p=1:t=2:c=2 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_section_contract_check tests.test_storyline_layer tests.test_root_guidance tests.test_pops_cli -v'
```

Expected: all tests `OK`。

- [ ] **Step 2: root smoke を計算ノードで実行する**

```sh
tssrun -p gr20001b -t 0:30:0 --rsc p=1:t=4:c=4 \
  bash -lc 'cd /LARGE1/gr20001/b36291/Github/paperops && make smoke'
```

Expected: command exit 0。

- [ ] **Step 3: template regression を静的レビューする**

次を確認する。

- `.agents` source と `.claude` wrapper の mirror
- generated/local/confidential file protection
- new schema は managed、new model state は project-owned
- legacy project は typed file 不在でも checker が動く
- new scaffold は typed file を含む
- migration note と CHANGELOG がある

- [ ] **Step 4: diff と commit history を確認する**

```sh
git status --short
git diff --check
git log -5 --oneline --decorate
```

Expected: whitespace error なし。未コミット差分があれば意図を確認して追加コミットする。

## Plan Self-Review

- Spec coverage: 承認済みタスクリストの P0-B を typed file、legacy dual-reader、schema、migration note、smoke まで含めている。
- Placeholder scan: 未確定の代用表現や後回し指示は残していない。
- Type consistency: `answer` は typed model、`one_sentence_answer` は legacy normalized keyとして明示的に分離する。`next_item_id` は ordered array の次 ID を参照する。
- Scope: PaperOps 2 全体ではなく、独立して release 可能な Results hierarchy slice に限定する。
