# PaperOps 2 P1-A Schema Kernel and Editorial Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 下流scaffold単体で動くversioned schema kernel、canonical hash、Editorial Model、合成fixture、検証CLIを実装し、P1-B以降の共通基盤を完成する。

**Architecture:** `template/scripts/paperops_schema.py` が安全なloader、PaperOps Schema Profile v1、canonical hashを提供し、`paperops_editorial.py` がEditorial固有のreference/semantic ruleを担当する。managed `registry.yml` とJSON Schemaは構造を定義し、project-owned YAMLはmanaged updateから分離する。`check-paperops-models.py` はphase別に両層を呼び、既存checkerと同じMarkdown reportを出す。

**Tech Stack:** Python 3.11+、標準ライブラリ、既存PyYAML依存、JSON Schema documents、YAML、`unittest`、Make、KUDPC `tssrun`

## Global Constraints

- push、release、GitHub Issue、PyPI publishは行わない。
- root層と`template/`層を混同しない。
- schema、registry、checkerはpaperops-managed、`_paperops/model/`はproject-ownedとする。
- project-owned stateを`pops update-paperops`で追加・上書きしない。
- typed documentが存在する場合、構文不正でもlegacy viewへfallbackしない。
- Schema Profile v1は許可keywordだけを実装し、未対応keywordとremote `$ref`をerrorにする。
- loaderはduplicate key、非有限数、読取不能documentをerrorにする。
- validation phaseは`schema / references / semantics / hash / all`を分離する。
- canonical hashは`semantic-v1`、SHA-256、sorted keys、array順保持、末尾改行なし、除外pathはversioned registryだけで指定する。
- P1-Aではclaim targetの実在確認を`reference.deferred` infoとし、P1-B未提供を明記する。
- fixtureは合成データだけを使い、private/raw/local/confidential情報を含めない。
- `template/` interface変更にはmigration noteと`CHANGELOG.md`更新を伴う。
- テストはログインノードで直接実行せず、`tssrun -p gr20001b`で計算ノードへ送る。

---

### Task 1: 安全なloader、Schema Profile v1、canonical hash

**Files:**
- Create: `template/scripts/paperops_schema.py`
- Create: `tests/test_paperops_schema.py`

**Interfaces:**
- Produces: `ModelFinding`, `DocumentLoadError`, `SchemaDefinitionError`
- Produces: `load_document(path: Path) -> Any`
- Produces: `validate_schema(document: Any, schema: dict[str, Any]) -> list[ModelFinding]`
- Produces: `canonical_bytes(value: Any, *, excluded_paths: tuple[str, ...] = ()) -> bytes`
- Produces: `semantic_hash(value: Any, *, excluded_paths: tuple[str, ...] = (), pointer: str = "") -> str`
- Consumes later: registry/schema task、Editorial semantic validator、checker CLI

- [ ] **Step 1: import helperとloaderのfailing testsを書く**

`tests/test_paperops_schema.py`は`template/scripts`を`sys.path`へ追加し、次を検査する。

```python
SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from paperops_schema import DocumentLoadError, load_document

def test_loader_rejects_duplicate_yaml_keys(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.yml"
        path.write_text("schema_version: 1\nschema_version: 2\n", encoding="utf-8")
        with self.assertRaisesRegex(DocumentLoadError, "document.duplicate_key"):
            load_document(path)

def test_loader_rejects_non_finite_number(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.yml"
        path.write_text("score: .nan\n", encoding="utf-8")
        with self.assertRaisesRegex(DocumentLoadError, "document.non_finite"):
            load_document(path)
```

- [ ] **Step 2: REDを計算ノードで確認する**

Run:

```bash
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_paperops_schema -v'
```

Expected: `ModuleNotFoundError: No module named 'paperops_schema'`。

- [ ] **Step 3: findingと安全なloaderを実装する**

`paperops_schema.py`へ次のpublic contractを実装する。

```python
@dataclass(frozen=True)
class ModelFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"

class DocumentLoadError(ValueError):
    pass

class SchemaDefinitionError(ValueError):
    pass

def load_document(path: Path) -> Any:
    """Load JSON/YAML, rejecting duplicate keys and non-finite numbers."""
```

PyYAMLの`SafeLoader`をsubclass化し、mapping constructorで同じkeyを二度見たら`document.duplicate_key`を含む`DocumentLoadError`を送出する。load後は再帰walkし、`math.isfinite`でないfloatを`document.non_finite`として拒否する。PyYAML import不能かつJSONでもない場合は`document.yaml_unavailable`とする。

- [ ] **Step 4: Schema Profileのfailing testsを追加する**

次のcasesを個別testにする。

```text
required:  schema={type: object, required: [name]} document={} -> schema.required at /name
type:      schema={type: array} document={} -> schema.type at root pointer ""
additional: object properties={name} additionalProperties=false、document={name: ok, extra: 1}
            -> schema.additional at /extra
local ref: $ref=#/$defs/item、item={type: string}、document="ok" -> findings=[]
remote ref: $ref=https://example.invalid/schema -> SchemaDefinitionError with schema.remote_ref
unsupported: schema keyword if -> SchemaDefinitionError with schema.unsupported_keyword
oneOf: integer/string branches accept 1 and "one" but reject [] with schema.one_of
additional subschema: unknown property value must satisfy {type: string}
```

各caseを独立test methodにし、codeとJSON Pointerをassertする。

- [ ] **Step 5: generic schema validatorを実装する**

許可keywordを定数化する。

```python
SUPPORTED_KEYWORDS = frozenset({
    "$schema", "$id", "title", "description", "type", "required",
    "properties", "additionalProperties", "items", "minItems",
    "maxItems", "uniqueItems", "enum", "const", "pattern",
    "minLength", "$defs", "$ref", "allOf", "anyOf", "oneOf",
})
```

schema definitionを先に再帰walkし、未対応keywordを`schema.unsupported_keyword`、`#/$defs/...`以外のrefを`schema.remote_ref`として拒否する。validationはtypeをPythonの`bool`と`int`で混同せず、findingをdocument順・pointer順で安定出力する。`oneOf`は成功branchがちょうど一つ、`anyOf`は一つ以上を要求する。

- [ ] **Step 6: canonical hashのfailing testsを追加する**

```text
mapping order: {a: 1, b: 2} と {b: 2, a: 1} は同hash
comment/line ending: 同じYAML semantic valueのLF/commentありとCRLF/commentなしは同hash
exact exclusion: /metadata/updated_atだけ異なる二documentは同hash、/metadata/other差は異なるhash
array order: [a, b] と [b, a] は異なるhash
semantic value: selected_story_id差は異なるhash
object pointer: pointer=/story_candidates/0 はそのsubrecord単体のhashと一致
non-finite: float("nan") はValueError with hash.non_finite
```

期待formatは`r"^sha256:[0-9a-f]{64}$"`。`/metadata/updated_at`だけが違うdocumentは同hash、`/metadata/other`が違えば異なるhashとする。

- [ ] **Step 7: canonicalizationを実装する**

JSON Pointerの`~0`/`~1`をdecodeし、exact pathだけを除外する。`pointer`指定時はsubrecordを選び、存在しなければ`KeyError`。serializationは次に固定する。

```python
json.dumps(
    normalized,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

hashは`"sha256:" + hashlib.sha256(payload).hexdigest()`。

- [ ] **Step 8: Task 1 suiteをGREENにする**

Task 1 Step 2と同じcommandを実行し、全test `OK`を確認する。

- [ ] **Step 9: コミットする**

```bash
git add template/scripts/paperops_schema.py tests/test_paperops_schema.py
git commit -m "型付きモデルを追加依存なしで安全に検証するため"
```

---

### Task 2: managed registry、Editorial schema、project-owned starter

**Files:**
- Create: `template/_paperops/defaults/schemas/registry.yml`
- Create: `template/_paperops/defaults/schemas/editorial-model.schema.json`
- Modify: `template/_paperops/defaults/schemas/results-hierarchy.schema.json`
- Create: `template/_paperops/model/editorial/editorial-model.yml`
- Create: `tests/test_editorial_model_schema.py`
- Modify: `tests/test_pops_cli.py`

**Interfaces:**
- Consumes: `load_document`, `validate_schema`, `semantic_hash`
- Produces: registry entries `editorial` and `results_hierarchy`
- Produces: `load_registry(root: Path) -> SchemaRegistry` in `paperops_schema.py`
- Produces: `RegistryEntry(name, schema_path, schema_version, authority, default_path, hash_profile, hash_excluded_paths)`

- [ ] **Step 1: registry resolutionのfailing testsを書く**

```text
resolve: template registryのeditorial entryがmanaged schema pathとproject default pathを返す
version: registry_version=2とvalidator_profile=unknownをそれぞれregistry.version/profile error
missing: schema filename欠損をregistry.schema_missing error
path: absolute schema/default pathと../ traversalをregistry.path error
starter: editorial starterをschema validateしerror=[]
```

starterはschema phaseでerrorなし、semantic phaseはTask 3まで未実装なのでここでは呼ばない。

- [ ] **Step 2: CLI managed/project境界のfailing testsを書く**

`tests/test_pops_cli.py`に次を追加する。

```text
test_init_contains_editorial_starter:
  pops initしたtargetに_paperops/model/editorial/editorial-model.ymlが存在する。
test_update_manages_schema_registry_and_checker_but_not_editorial_state:
  旧scaffold fixtureからregistry.yml、editorial schema、2 checker module、editorial-model.ymlを欠損させる。
  update planはmanaged registry/schema/scriptsだけをmissingへ列挙する。
  --apply後もproject-owned editorial-model.ymlは存在せず、managed filesだけが追加される。
```

新規`pops init`ではstarterが存在することも別assertする。

- [ ] **Step 3: REDを計算ノードで確認する**

Run:

```bash
tssrun -p gr20001b -t 0:12:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_editorial_model_schema tests.test_pops_cli -v'
```

Expected: registry/schema/starter未作成でFAIL。

- [ ] **Step 4: registry loaderを実装する**

`paperops_schema.py`へ次を追加する。

```python
@dataclass(frozen=True)
class RegistryEntry:
    name: str
    schema_path: Path
    schema_version: int
    authority: str
    default_path: Path
    hash_profile: str
    hash_excluded_paths: tuple[str, ...]

@dataclass(frozen=True)
class SchemaRegistry:
    version: int
    validator_profile: str
    entries: dict[str, RegistryEntry]

```

`load_registry(root: Path) -> SchemaRegistry`はregistryを安全にloadし、全entryを検証して上記dataclassへ変換する。失敗はcodeを含む`SchemaDefinitionError`にする。

registry pathは`root/_paperops/defaults/schemas/registry.yml`。version/profileはそれぞれ`1`/`paperops-schema-v1`だけを許可し、schemaはregistry directory内のfilename、default pathはproject root内相対pathだけを許可する。

- [ ] **Step 5: registry.ymlを作る**

spec記載の二entryを作り、Editorial entryだけ`hash_excluded_paths: [/metadata/updated_at]`を持たせる。Results entryは空arrayにする。

- [ ] **Step 6: Editorial JSON Schemaを作る**

top-levelは次をrequiredにし、`additionalProperties: false`とする。

```text
schema_version, model_id, revision, reader_transformation,
story_candidates, selected_story_id, single_candidate_reason,
claim_roles, argument_moves, visual_obligations,
results_hierarchy, extensions, metadata
```

ID patternは`EDT-* / STY-* / MOV-* / VIS-* / CLM-* / FIG-* / RHI-*`。四claim roleをrequiredにし、各roleは`claim_ids`と`none_reason`だけを持つ。`extensions`はobjectでadditionalPropertiesを許可し、key formatはTask 3 semanticで検査する。starterを許すためcandidate/move/item arrayのschema minItemsは0、semantic strict ruleはTask 3へ置く。

- [ ] **Step 7: project-owned starterを作る**

specのstarter contractを完全に配置する。`extensions: {}`を含める。concrete story/move IDは置かず、starter placeholderであることを冒頭commentに記す。

- [ ] **Step 8: Results schemaをprofile適合させる**

既存意味を変えず、registry version contractで利用できることをtestする。未対応keywordを追加しない。schema version、ID pattern、chain semanticsは既存checkerと一致させる。

- [ ] **Step 9: managed boundaryを確認してGREENにする**

Task 2 Step 3と同じcommandを実行。新規initはstarterを含み、updateはmanaged registry/schema/scriptsだけを扱い、欠損project stateを追加しないことを確認する。

- [ ] **Step 10: コミットする**

```bash
git add template/_paperops/defaults/schemas template/_paperops/model/editorial/editorial-model.yml \
  template/scripts/paperops_schema.py tests/test_editorial_model_schema.py tests/test_pops_cli.py
git commit -m "managed schemaと論文固有Editorial状態を分離するため"
```

---

### Task 3: Editorial reference / semantic validation

**Files:**
- Create: `template/scripts/paperops_editorial.py`
- Create: `tests/test_editorial_model_semantics.py`

**Interfaces:**
- Consumes: `ModelFinding`, loaded Editorial/Results documents
- Produces: `validate_editorial_references(editorial: dict[str, Any], results: dict[str, Any]) -> list[ModelFinding]`
- Produces: `validate_editorial_semantics(editorial: dict[str, Any], *, strict: bool) -> list[ModelFinding]`
- Produces: `validate_extension_keys(extensions: dict[str, Any]) -> list[ModelFinding]`

- [ ] **Step 1: reference validationのfailing testsを書く**

valid minimal document helperをtest内に作り、次を個別検査する。

```text
reference.duplicate       duplicate STY/MOV/VIS IDs
reference.dangling        selected story, next move, result item, story move ref
reference.cycle           move chain cycle
reference.order           position gap / array-next mismatch
reference.deferred(info)  CLM/FIG external target before P1-B
reference.path            absolute path / .. traversal
```

deferred findingは`severity == "info"`をassertする。

- [ ] **Step 2: semantic validationのfailing testsを書く**

```text
semantic.story_selection  selected exactly once and reasons
semantic.story_count      one candidate requires single_candidate_reason
semantic.claim_role       empty requires reason; nonempty forbids reason; no duplicate role
semantic.move             stance and nonblank reader/assertion in strict
semantic.visual           waived reason; satisfied FIG ref
semantic.placeholder      starter warnings vs strict errors
semantic.extension        x-owner-name key format
```

- [ ] **Step 3: REDを計算ノードで確認する**

```bash
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_editorial_model_semantics -v'
```

Expected: `ModuleNotFoundError: No module named 'paperops_editorial'`。

- [ ] **Step 4: reference validatorを実装する**

ID indexをtype別に一度だけ作る。Results IDは参照documentの`items[].id`から取る。move graphは配列順、position、next edgeを別々に検査し、DFS colorでcycleを検出する。既にduplicateのIDはdangling解析に使わず、二次findingを抑える。

- [ ] **Step 5: semantic validatorを実装する**

placeholder判定は既存`paperops_checks.meaningful_value`へ依存せず、このmodule内の小さなpure helperに固定する。advisoryではplaceholderをwarning、strictではerror。構造不正はschema phaseの責務なので、期待typeでない値はskipし例外を出さない。

- [ ] **Step 6: extension key validatorを実装する**

patternを`^x-[a-z0-9][a-z0-9._-]*-[a-z0-9][a-z0-9._-]*$`に固定する。valueのduplicate/non-finiteはloaderが既に拒否する。

- [ ] **Step 7: GREENと既存Results testsを確認する**

```bash
tssrun -p gr20001b -t 0:12:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_editorial_model_semantics tests.test_section_contract_check -v'
```

Expected: 全test `OK`。

- [ ] **Step 8: コミットする**

```bash
git add template/scripts/paperops_editorial.py tests/test_editorial_model_semantics.py
git commit -m "Editorial判断の参照欠損と意味不整合を分けて検出するため"
```

---

### Task 4: phase別checker CLIとMake wiring

**Files:**
- Create: `template/scripts/check-paperops-models.py`
- Create: `tests/test_paperops_model_check.py`
- Modify: `Makefile`
- Modify: `template/Makefile`
- Modify: `tests/test_makefile_profiles.py`

**Interfaces:**
- Consumes: registry/schema/editorial modules
- Produces CLI: `--root`, `--model`, `--phase`, `--strict`, `--print-hash`, `--document`, `--results-document`
- Produces Make target: `schema-check`

- [ ] **Step 1: CLI failing testsを書く**

`run_python_script`で次を検査する。

```text
starter advisory: exit 0、Warningsにsemantic.placeholder
starter strict: exit 1、Errorsにsemantic.placeholder
schema prerequisite: unknown field documentはschema.additionalだけを出しreference.danglingを出さない
phase references: dangling refを出しsemantic.story_countを出さない
deferred: CLM/FIG refsはInfoにreference.deferred、exit 0
print hash clean: valid fixtureはhash一行、invalid documentはexit 1でhashを出さない
override: --documentと--results-documentのRHI参照を使いdefault starterを読まない
usage: unknown --model/--phaseはargparse exit 2
copied scaffold: copy_template後のstarter code/severity集合がsource templateと一致
```

report headingは`# paperops-model-check`、sectionは`Errors / Warnings / Info`。finding formatは`` `[code] pointer`: message ``。

- [ ] **Step 2: Make wiring failing testsを書く**

root/template両Makefileに`schema-check` targetがあり、root `SMOKE_CHECKS`とtemplate `AUDIT_CHECKS`に含まれ、`FINISH_MANUSCRIPT_CHECKS`や`PRE_SUBMIT_CHECKS`へはP1-Aで直接追加しないことをassertする。

- [ ] **Step 3: REDを計算ノードで確認する**

```bash
tssrun -p gr20001b -t 0:12:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_paperops_model_check tests.test_makefile_profiles -v'
```

- [ ] **Step 4: checker orchestrationを実装する**

schema failure時はreferences/semantics/hashをskipする。`--phase references`でもschema loadは安全のため実施するが、schema findingsをreportへ出さずschema errorなら`phase.prerequisite` errorにする。`--print-hash`はcleanなsingle modelだけ許可する。

Infoを既存`emit_findings`へ渡さず、checkerがErrors/Warnings/Infoをpartitionして出力し、exit codeはerrorまたは`strict`時のwarningだけで1とする。

- [ ] **Step 5: Make targetsを実装する**

root:

```make
schema-check:
	$(PYTHON) template/scripts/check-paperops-models.py --root template
```

template:

```make
schema-check:
	$(PYTHON) scripts/check-paperops-models.py --root .
```

`.PHONY`と指定aggregateへ追加する。

- [ ] **Step 6: GREENにする**

Task 4 Step 3と同じcommandを再実行し全test `OK`。

- [ ] **Step 7: コミットする**

```bash
git add template/scripts/check-paperops-models.py tests/test_paperops_model_check.py \
  Makefile template/Makefile tests/test_makefile_profiles.py
git commit -m "型付きモデルをphase別に日常検査できるようにするため"
```

---

### Task 5: 三つの合成fixtureとinvalid corpus

**Files:**
- Create: `tests/fixtures/editorial/mechanism-led/editorial-model.yml`
- Create: `tests/fixtures/editorial/mechanism-led/results-hierarchy.yml`
- Create: `tests/fixtures/editorial/mechanism-led/fixture.yml`
- Create: `tests/fixtures/editorial/boundary-led/editorial-model.yml`
- Create: `tests/fixtures/editorial/boundary-led/results-hierarchy.yml`
- Create: `tests/fixtures/editorial/boundary-led/fixture.yml`
- Create: `tests/fixtures/editorial/negative-result-led/editorial-model.yml`
- Create: `tests/fixtures/editorial/negative-result-led/results-hierarchy.yml`
- Create: `tests/fixtures/editorial/negative-result-led/fixture.yml`
- Create: `tests/fixtures/editorial/invalid/*.yml`
- Create: `tests/test_editorial_fixtures.py`

**Interfaces:**
- Consumes: checker CLI and semantic hash
- Produces: P1-B/P6 comparison corpus with stable expected hash/finding codes

- [ ] **Step 1: fixture contractのfailing testを書く**

三directoryを列挙し、各`fixture.yml`が次を持つことをassertする。

```yaml
fixture_version: 1
category: mechanism-led
editorial_document: editorial-model.yml
results_document: results-hierarchy.yml
expected_hash: sha256:<64hex>
expected_diagnostics: []
synthetic: true
```

各Editorial documentは最低2 story candidates、selected/rejected reasons、四role、3 moves、1 visual obligation、3 Results item refsを持つ。

- [ ] **Step 2: fixture未作成のREDを確認する**

fixture未作成の状態で次を実行し、三categoryの欠損でFAILすることを確認する。

```bash
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_editorial_fixtures -v'
```

Expected: fixture directory/file未作成を理由にFAIL。

- [ ] **Step 3: valid fixtureを作る**

実在研究名・DOI・raw pathを使わず、`synthetic-control-*`の語彙で三categoryを区別する。claim/figure refsはdeferred infoになるためfixture manifestのexpected diagnosticsへ`reference.deferred`を含めるが、strict exitは0にする。

- [ ] **Step 4: expected hashをcheckerから取得して固定する**

各fixtureへ`--print-hash --document <case>/editorial-model.yml --results-document <case>/results-hierarchy.yml`を実行し、得たhashをmanifestへ記録する。hashを手計算しない。

- [ ] **Step 5: invalid corpusのfailing testsを書く**

最低限次のfile/caseと期待codeをtable-driven testにする。

```text
duplicate-key.yml              document.duplicate_key
duplicate-id.yml               reference.duplicate
invalid-stance.yml             schema.enum
dangling-story.yml             reference.dangling
dangling-result.yml            reference.dangling
move-cycle.yml                 reference.cycle
move-order-gap.yml             reference.order
empty-role-reason.yml          semantic.claim_role
single-story-no-reason.yml     semantic.story_count
absolute-results-path.yml      reference.path
traversal-results-path.yml     reference.path
unknown-field.yml              schema.additional
non-finite.yml                 document.non_finite
unsupported-schema-keyword.yml schema.unsupported_keyword
```

unsupported schema caseだけ一時schema override helperでkernelを直接呼ぶ。

- [ ] **Step 6: fixture testsを計算ノードで実行する**

```bash
tssrun -p gr20001b -t 0:15:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_editorial_fixtures -v'
```

Expected: valid三件strict success、hash一致、invalid全case期待code、`OK`。

- [ ] **Step 7: privacy scan testを追加する**

fixture全textを走査し、`/home/`, `/Users/`, `/LARGE`, `BEGIN .* PRIVATE KEY`, `sk-`、`raw reviewer`がないこと、`synthetic: true`をassertする。

- [ ] **Step 8: コミットする**

```bash
git add tests/fixtures/editorial tests/test_editorial_fixtures.py
git commit -m "Editorial設計を同じ合成入力で反復評価するため"
```

---

### Task 6: guide-only migration、利用者interface、docs、最終検証

**Files:**
- Modify: `src/paperops/cli/migrations.py`
- Modify: `tests/test_pops_cli.py`
- Modify: `docs/migrations/v0.md`
- Modify: `template/AGENTS.md`
- Modify: `template/CLAUDE.md`
- Modify: `template/README.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/cli.md`
- Modify: `docs/current-specification.md`
- Modify: `docs/skill-catalog.md`
- Modify: `docs/paperops2-disposition.md`
- Modify: `CHANGELOG.md`
- Modify: `_handoff/TODO.md`
- Create: `tests/test_p1a_documentation.py`
- Modify: `tests/test_paperops2_design_docs.py`

**Interfaces:**
- Produces migration: `M0-0004 Adopt the Editorial Model schema kernel`
- Preserves: M0-0001〜M0-0003 behavior and project-owned state

- [ ] **Step 1: migrationのfailing testsを書く**

```text
list/show: M0-0004、Editorial Model、schema-check、project-ownedを表示
apply: moves=()で、欠損editorial-model.ymlを作らずmanifestだけmigration appliedへ進める
guide order: strict commandがauthority switchとlegacy view削除より前に記載される
```

`moves == ()`、apply後に欠損`_paperops/model/editorial/editorial-model.yml`が作られないことをassertする。

- [ ] **Step 2: documentation regression failing testsを書く**

各surfaceを個別に読み、次をassertする。

```text
managed registry/schema/checker vs project-owned model
schema / references / semantics / hash phases
make schema-check
M0-0004 strict validation order
legacy controlled view retained through P2
P1-B Research/Manuscript/Issue/Publication not delivered
three synthetic fixture categories
canonical semantic-v1 hash
```

- [ ] **Step 3: REDを計算ノードで確認する**

```bash
tssrun -p gr20001b -t 0:15:0 --rsc p=1:t=2:c=2 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_pops_cli tests.test_p1a_documentation -v'
```

- [ ] **Step 4: M0-0004を登録する**

title、summary、notesにproject-owned state非生成、`make schema-check` advisory、明示`--strict`成功、legacy view維持を記す。`registered_migrations()`末尾へ追加する。

- [ ] **Step 5: migration guideを書く**

updateでmanaged files取得→project-owned model手動作成→strict schema/reference/semantics→hash記録→人間承認→authority切替、の順を固定する。自動move、dual-write、legacy削除を行わないと明記する。

- [ ] **Step 6: downstream interface docsを更新する**

`template/AGENTS.md`と`CLAUDE.md`は同じcontractを持たせる。READMEは新規projectと既存projectを分け、既存はM0-0004までEditorial starterを自動取得しないと説明する。CLI docsは`schema-check` phaseとexit behaviorを記す。

- [ ] **Step 7: architecture/index/catalog/CHANGELOGを更新する**

P1-Aの提供範囲とP1-B未提供を明記する。Results hierarchyをEditorial Model接続へ位置付けるが、旧checkerやcontrolled viewを削除しない。CHANGELOGはmanaged/project-owned境界と利用者のopt-in手順を含める。

`docs/paperops2-disposition.md`には`template/scripts/check-paperops-models.py`とroot/templateの`schema-check` targetを八列の個別rowとして追加する。`tests/test_paperops2_design_docs.py`のdynamic checker/Make target inventoryが新surfaceを完全一致で検査し、存在しない別inventory文書を正本にしない。

- [ ] **Step 8: TODOを実績同期する**

P1全体を完了にせず、P1-A縦切りだけを完了として追記する。Research/Manuscript/Issue/Publication、全model cross-ref、dependency hashはP1-B残件とする。

- [ ] **Step 9: focused suitesを計算ノードで実行する**

```bash
tssrun -p gr20001b -t 0:20:0 --rsc p=1:t=4:c=4 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest \
   tests.test_paperops_schema tests.test_editorial_model_schema \
   tests.test_editorial_model_semantics tests.test_paperops_model_check \
   tests.test_editorial_fixtures tests.test_pops_cli \
   tests.test_p1a_documentation -v'
```

Expected: 全test `OK`。

- [ ] **Step 10: full smokeを計算ノードで実行する**

```bash
tssrun -p gr20001b -t 0:30:0 --rsc p=1:t=4:c=4 bash -lc \
  'cd /LARGE1/gr20001/b36291/Github/paperops && make smoke'
```

Expected: exit 0。starter placeholder warningと`reference.deferred` infoだけを許容する。

- [ ] **Step 11: 静的監査する**

```bash
git diff --check
rg -n 'TBD|TODO|未定|要検討' \
  template/_paperops/defaults/schemas template/scripts/paperops_schema.py \
  template/scripts/paperops_editorial.py docs/migrations/v0.md
```

Expected: whitespace errorなし、placeholder該当なし。

- [ ] **Step 12: コミットする**

```bash
git add src/paperops/cli/migrations.py tests/test_pops_cli.py docs/migrations/v0.md \
  template/AGENTS.md template/CLAUDE.md template/README.md README.md \
  docs/architecture.md docs/cli.md docs/current-specification.md docs/skill-catalog.md \
  docs/paperops2-disposition.md CHANGELOG.md tests/test_p1a_documentation.py \
  tests/test_paperops2_design_docs.py
git commit -m "既存論文を保護しながらEditorial Modelへ移れるようにするため"
```

`_handoff/TODO.md`はignored ledgerなのでcommit対象外。

- [ ] **Step 13: 完了監査する**

specの完了条件を、schema/registry/starter、finding code tests、fixture hash、managed boundary test、M0-0004、docs test、focused output、smoke outputへ一項目ずつ対応付ける。`git status --short --branch`がcleanで、mainは未pushの先行commitだけであることを確認する。
