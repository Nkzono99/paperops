# PaperOps 2 P1-A: Schema Kernel と Editorial Model 縦切り

## 目的

PaperOps 2 の五つの論理モデルを一度に実装する前に、schema registry、dependency-free validator、cross-reference validation、canonical hash、project-owned model state、合成 fixture の一周を Editorial Model で完成させる。

この縦切りは P1-B で Research / Manuscript / Issue / Publication Model を追加するときの共通実装となる。P1-A の完了だけで shadow migration、Writer、workflow cutover、v2-authoritative を提供済みとは扱わない。

## スコープ

P1-A で実装するもの:

1. paperops-managed schema registry
2. PaperOps Schema Profile v1 の validator
3. Editorial Model JSON Schema と project-owned starter state
4. schema validation と cross-reference / semantic validation の分離
5. canonical serialization と SHA-256 hash
6. mechanism-led / boundary-led / negative-result-led の三つの合成 fixture 本体
7. advisory / strict checker、Make target、migration guide、利用者向け文書

P1-A で実装しないもの:

- Research / Manuscript / Issue / Publication Model schema
- legacy card から Editorial Model への自動変換
- project state の managed update
- shadow compare、atomic migration、rollback snapshot
- section compiler、Writer packet、TeX patch
- workflow state cutover、public skill 集約、semantic judge、release

## 配置と所有権

### Managed files

- `_paperops/defaults/schemas/registry.yml`
- `_paperops/defaults/schemas/editorial-model.schema.json`
- `_paperops/defaults/schemas/results-hierarchy.schema.json`
- `scripts/paperops_schema.py`
- `scripts/check-paperops-models.py`

これらは `pops update-paperops` の managed update 対象とする。

### Project-owned files

- `_paperops/model/editorial/editorial-model.yml`
- `_paperops/model/editorial/results-hierarchy.yml`

新規 `pops init` は starter を配置する。既存 project へ managed update で追加・上書きしない。既存 project は guide-only migration を選択し、strict validation 成功後にだけ新正本として扱う。

### Test-only files

- `tests/fixtures/editorial/mechanism-led/`
- `tests/fixtures/editorial/boundary-led/`
- `tests/fixtures/editorial/negative-result-led/`

fixture は合成データだけを含み、private project、raw reviewer text、credential、絶対 path、未公開 raw data を含めない。

## Schema registry

`registry.yml` は model 名から schema、authority、validator profile、hash profile、default project path を解決する managed registry とする。

各 entry は最低限次を持つ。

```yaml
registry_version: 1
validator_profile: paperops-schema-v1
models:
  editorial:
    schema: editorial-model.schema.json
    schema_version: 1
    authority: project-owned
    default_path: _paperops/model/editorial/editorial-model.yml
    hash_profile: semantic-v1
    hash_excluded_paths:
      - /metadata/updated_at
  results_hierarchy:
    schema: results-hierarchy.schema.json
    schema_version: 1
    authority: project-owned
    default_path: _paperops/model/editorial/results-hierarchy.yml
    hash_profile: semantic-v1
```

registry は project state を列挙するだけで書き換えない。未知の model、未知の registry version、schema file 欠損、registry と document の schema version 不一致は schema-phase error とする。

## PaperOps Schema Profile v1

下流 checker は追加の Python package を要求しない。`scripts/paperops_schema.py` に標準ライブラリだけで JSON Schema の限定 profile を実装する。

許可する keyword:

- `$schema`, `$id`, `title`, `description`
- `type`, `required`, `properties`, `additionalProperties`
- `items`, `minItems`, `maxItems`, `uniqueItems`
- `enum`, `const`, `pattern`, `minLength`
- `$defs`, `$ref`
- `allOf`, `anyOf`, `oneOf`

registry に登録された schema が未対応 keyword を使う場合、無視せず schema-definition error とする。profile は JSON Schema Draft 2020-12 の全実装を名乗らない。

`$ref` は同一schema内の `#/$defs/...` だけを許可する。HTTP、file URI、別fileへの参照はnetworkやlocal pathへ依存するためschema-definition errorとする。`additionalProperties` はbooleanまたはsubschemaを受け取れる。

validator は machine-readable finding code、JSON Pointer、message を返す。

```text
schema.required       /story_candidates/0/thesis
schema.type           /argument_moves
schema.additional     /unknown_field
reference.dangling    /selected_story_id
reference.duplicate   /argument_moves/1/id
semantic.story_count  /story_candidates
hash.non_finite       /metrics/score
```

advisory mode は starter placeholder を warning にできるが、構文不正、未知schema version、duplicate key、duplicate ID、dangling reference は常に error とする。strict mode は未記入の必須semantic fieldもerrorにする。

## 安全なdocument loader

YAML / JSON loader は duplicate mapping key を検出し、後勝ちで上書きしない。YAML comment、改行コード、mapping記述順はload後のsemantic valueに含めない。

非有限数 `NaN`、`Infinity`、`-Infinity` はschema validationとhashの両方で拒否する。読み取れないdocumentが存在する場合、legacy viewへfallbackしない。

## Editorial Model

starter document のtop-level contractは次とする。

```yaml
schema_version: 1
model_id: EDT-0001
revision: 1
reader_transformation:
  reader_before: 未記入
  reader_after: 未記入
  why_it_matters: 未記入
story_candidates: []
selected_story_id: ""
single_candidate_reason: ""
claim_roles:
  foreground: {claim_ids: [], none_reason: 未記入}
  supporting: {claim_ids: [], none_reason: 未記入}
  supplement: {claim_ids: [], none_reason: 未記入}
  cut: {claim_ids: [], none_reason: 未記入}
argument_moves: []
visual_obligations: []
results_hierarchy:
  document: _paperops/model/editorial/results-hierarchy.yml
  item_ids: []
metadata:
  updated_at: ""
```

### Story candidate

各 candidate は stable `STY-*` ID、label、thesis、result order、argument move refs、status を持つ。status は `candidate / selected / rejected` のいずれかとする。

- selected はちょうど一件で `selected_story_id` と一致する。
- rejected candidate は非空の `rejection_reason` を持つ。
- selected candidate は非空の `selection_reason` を持つ。
- 原則二候補以上とする。
- 一候補だけの場合は非空の `single_candidate_reason` を要求する。
- 形式的な第二候補を捏造することを要求しない。

### Claim roles

`foreground / supporting / supplement / cut` の四roleは常に存在する。各roleは `claim_ids` arrayと `none_reason` を持つ。arrayが空なら `none_reason`、非空なら `none_reason` は空にする。同一claimを複数roleへ重複登録しない。

P1-Aでは `CLM-*` の外部参照形式を検査するが、Research Modelが未実装なのでclaim targetの実在確認は `deferred reference` として明示的に報告する。黙ってvalid扱いにもdangling扱いにもしない。P1-Bで実在確認へ切り替える。

`reference.deferred` はP1-Aではinfo severityとし、strict validationを失敗させない。P1-BでResearch Modelがregistryへ追加された時点で、同じ参照を実在確認付きのerror/warning判定へ移行する。

### Argument moves

各moveは `MOV-*` ID、連番position、stance、reader question、assertion、claim refs、results item refs、`next_move_id` を持つ。

stanceは `assert / reject / boundary / hold`。positionは1から欠番なく配列順と一致する。`next_move_id` は次のmoveを指し、末尾だけ空文字とする。duplicate、dangling、cycle、順序不一致を別codeで検出する。

### Visual obligations

各obligationは `VIS-*` ID、reader task、takeaway、claim refs、preferred form、statusを持つ。statusは `planned / satisfied / waived`。`waived` は理由を要求し、`satisfied` は `FIG-*` referenceを要求する。

### Results hierarchy 接続

`results_hierarchy.document` はproject rootからの相対pathだけを許可し、絶対pathと `..` traversalを拒否する。`item_ids` は参照先documentの `RHI-*` IDへ解決し、欠損を `reference.dangling` とする。

## Extension field

schemaで定義されないtop-level fieldは `schema.additional` として拒否する。拡張は明示的な `extensions` mapping内だけに置く。

extension keyは `x-<owner>-<name>` 形式とし、ownerとnameはlowercase英数字を先頭にしたlowercase英数字・`.`・`_`・`-`だけを許可する。値はJSON互換のscalar、array、mappingを許可するが、duplicate keyと非有限数を拒否する。extension valueはsemantic hashへ含める。特定extensionをhashから除外する場合はschema registryのversioned `hash_excluded_paths`へJSON Pointerを追加し、黙って除外しない。

## Validation phases

checker は次のphaseを独立実行できる。

1. `schema`: registry、loader、schema keyword、型、必須field、未知field
2. `references`: duplicate ID、local reference、results hierarchy接続、deferred external reference
3. `semantics`: story selection、claim role、move chain、visual obligation、placeholder
4. `hash`: canonical serializationとexpected hash比較
5. `all`: 上記を順に実行

schema phaseが失敗したdocumentには後続phaseを実行せず、二次的な例外を増やさない。phaseごとのfinding codeを保ち、schema errorとdangling referenceを同じmessageへ潰さない。

## Canonical hash

hash profile `semantic-v1` は次で固定する。

- YAML / JSONを安全にloadしたsemantic valueを入力とする。
- object keyはUnicode code point順にsortする。
- array順は保持する。
- JSON serializationはUTF-8、`ensure_ascii=false`、separatorは`,`と`:`、末尾改行なし。
- integerとfinite floatはJSON numberとして保持し、NaN / Infinityを拒否する。
- schema versionとstable IDはhash対象に含める。
- registryのJSON Pointerで指定したfieldだけを除外する。
- P1-Aの除外pathは `/metadata/updated_at` のみとする。
- hash表現は `sha256:<64 lowercase hex>` とする。

同じsemantic valueでmapping順、YAML comment、line endingだけが異なる入力は同じhashになる。story thesis、selected story、claim role、move order、results item refの変更は異なるhashになる。

object-level hash APIはJSON Pointerでsubrecordを選べる。P1-B以降のdependency hashはこのAPIを使うが、P1-Aではdependency graph全体を実装しない。

## Checker CLI

`scripts/check-paperops-models.py` は次を提供する。

```text
python scripts/check-paperops-models.py --root . --model editorial --phase all
python scripts/check-paperops-models.py --root . --model editorial --strict
python scripts/check-paperops-models.py --root . --model editorial --print-hash
python scripts/check-paperops-models.py --root . --model editorial --document <fixture>
```

defaultはregistryの全modelをadvisory検査する。`--print-hash` はvalidation成功時だけstdoutへhashを出す。findingがある通常出力は既存checkerのMarkdown report shapeに合わせる。

`make schema-check` をrootとtemplateへ追加する。root smokeとtemplate auditにadvisoryで配線し、finish / pre-submitへ追加する時期はP1-Bで全modelが揃った後に判断する。

## Fixture

三fixtureはそれぞれ `editorial-model.yml` と `results-hierarchy.yml` を持つ。

- mechanism-led: mechanism claimを段階的に立証しalternativeをrejectする。
- boundary-led: 成立条件、破綻境界、適用範囲をforegroundにする。
- negative-result-led: null resultから仮説または測定限界を更新する。

各fixtureは最低二候補、selected/rejected理由、四claim role、ordered moves、visual obligation、三件以上のResults itemを持つ。期待hashと期待diagnosticをfixture manifestに記録する。

invalid variantsは最低限次を含む。

- duplicate YAML key
- duplicate ID
- invalid status / stance
- dangling selected story / move / Results item
- move cycle / order gap
- empty claim role without reason
- one story without reason
- absolute path / traversal
- unknown field
- non-finite number

## Migration と互換性

M0-0004相当のguide-only migrationを既存 `pops migrate list/show/apply` に登録する。自動moveやproject state生成は行わない。

既存projectは次の順でopt-inする。

1. managed registry、schema、checkerをupdateで受け取る。
2. starterとfixtureを参照してproject-owned Editorial Modelを作る。
3. `--strict`でschema / reference / semanticsを通す。
4. hashを記録する。
5. downstream workflowで明示承認後にEditorial typed authorityとして扱う。

legacy controlled authoring viewはP2 migration完了まで削除しない。typed fileが存在する場合、不正でもlegacyへfallbackしない。

## テスト

- schema profile keywordとunsupported keyword
- safe loader duplicate key
- registry resolutionとversion mismatch
- starter advisory / strict
- fixture三件のstrict successと期待hash
- invalid variantsごとのfinding code
- schema failure後にreference phaseを走らせない
- mapping order / comment / CRLFに対するhash安定性
- semantic変更に対するhash変化
- object-level hash
- managed schema/checkerはupdate対象、project modelは非対象
- source tree / copied scaffoldで同じchecker結果
- migration list/show/applyはproject stateを変更しない
- root/template Make target wiring

`template/` interface、schema、scriptを変更するため最終gateはKUDPC計算ノード上の `make smoke` とする。

## 完了条件

- Editorial Modelがschema、reference、semanticsの三層でstrict validationを通る。
- 三fixtureの期待hashが安定し、意味変更でhashが変わる。
- invalid caseがduplicate、dangling、status、cycle、path、unknown field、non-finiteを別codeで報告する。
- Results hierarchyとの接続を実在IDまで検査する。
- managed registry/schema/checkerとproject-owned model stateの更新境界がテストされる。
- 既存projectは自動変更されず、guide-only migrationでopt-inできる。
- legacy controlled viewとtyped authorityの移行境界が文書化される。
- P1-B以降を実装済みと表現しない。
- focused testsと`make smoke`が成功する。
