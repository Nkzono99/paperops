# PaperOps 2 P1-B: 四モデル・横断参照・dependency hash

## 目的

P1-A の schema kernel と Editorial Model 縦切りを拡張し、Research / Manuscript / Issue / Publication の残る四つの論理モデルを project-owned typed state として追加する。既存 card、workflow、submission ledger が保持している判断を落とさずに表現できる schema とし、全モデルの ID 解決、承認状態、dependency hash、selective stale を deterministic checker で検査する。

P1-B はモデルと検査境界を提供するサイクルである。legacy artifact からの自動変換と authority 切替は P2、section compiler と Writer packet は P3、workflow command の新モデル移行は P4 で扱う。このサイクルでは既存 card、workflow、ledger を削除・上書きしない。

## 採用する物理構成

論理モデルを五つの巨大 YAML と一対一にしない。更新頻度と不変性に応じて次を使い分ける。

- Research、Manuscript、Issue は `index.yml` と per-ID record を使う。
- Publication は current state と round ledger の整合を一括検査する必要があるため、小さな集約 file を使う。
- Editorial は P1-A の集約 file と Results hierarchy file を維持し、P2 の shadow migration までは分割しない。
- index は discovery、順序、record path、期待 revision/hash だけを持ち、record 内容を複製しない。
- record path は project root 相対の正規 path とし、絶対 path、`..`、symlink による project root 脱出を拒否する。

配置は次で固定する。

```text
_paperops/model/
  research/
    index.yml
    claims/CLM-*.yml
    results/RES-*.yml
    figures/FIG-*.yml
    sources/SRC-*.yml
    gates/GATE-*.yml
  editorial/
    editorial-model.yml
    results-hierarchy.yml
  manuscript/
    index.yml
    sections/SEC-*.yml
    blocks/BLK-*.yml
  issues/
    index.yml
    feedback/FB-*.yml
    analysis/AREQ-*.yml
    writing/WREQ-*.yml
    responses/RSP-*.yml
    rounds/RVW-*.yml
  publication/
    publication-model.yml
```

starter index は空の `records` 配列を許す。starter 用に架空の研究判断や査読履歴を tracked project state へ作らない。合成 fixture では全 record family を実体化する。

## 共通 record envelope

Research / Manuscript / Issue の各 record は最低限次を持つ。

```yaml
schema_version: 1
record_type: claim
id: CLM-0001
revision: 1
status: draft
dependencies: []
approvals: []
extensions: {}
metadata:
  updated_at: ""
```

`dependencies` は次の形式とする。

```yaml
- target_id: RES-0001
  relation: supported_by
  expected_revision: 2
  expected_hash: sha256:<64 lowercase hex>
```

- `target_id` と `relation` は semantic field である。
- `expected_revision` と `expected_hash` は参照を確定した時点の dependency snapshot である。
- `expected_hash` は常に必須とする。target が独立した `revision` を持つ場合は `expected_revision` も必須とし、現在値のどちらかが違えば `dependency.stale` とする。Editorial の move や Results item のように独立 revision を持たない subrecord は object-level hash だけで固定し、所有 document の revision を捏造しない。
- dependency の配列順は意味を持たない。hash 計算では `(target_id, relation)` で整列する。
- 同じ `(target_id, relation)` の重複は `reference.duplicate` とする。
- 自己参照は、schema が明示的に許可する relation 以外は拒否する。P1-B では自己参照を許可する relation はない。

`approvals` は approval history を上書きせず追加する配列である。

```yaml
- approval_id: APR-0001
  kind: scientific_scope
  decision: approved
  object_revision: 1
  object_hash: sha256:<64 lowercase hex>
  actor: human
  note: ""
```

`kind` は `scientific_scope / editorial_choice / submission / authorship / license / external_share / reviewer_response / scope_expansion`、`decision` は `approved / rejected / superseded` とする。actor の credential、email、署名値は保存しない。`object_hash` は必須、`object_revision` は対象が独立 revision を持つ場合に必須とする。現在 revision/hash に一致する `approved` record が必要な場所では、古い approval を `approval.stale`、存在しない場合を `approval.missing` とする。

独立 revision を持つ record の canonical subject hash は `hash_excluded_paths` で `/approvals` と `/metadata/updated_at` を除外する。approval history はその subject hash/revision への attestation として別に検査し、approval の追加・decision 変更だけでは承認対象 object の hash/revision を進めない。ただし approval の有効性と workflow gate は `approval.*` finding により変化する。これにより approval 自身の `object_hash` を含む自己参照 hash を作らない。

## Index contract

各 index は `model_name`、`schema_version`、`index_revision`、`records`、`extensions`、`metadata` を持つ。record row は次だけを保持する。

```yaml
- id: CLM-0001
  record_type: claim
  document: _paperops/model/research/claims/CLM-0001.yml
  expected_revision: 1
  expected_hash: sha256:<64 lowercase hex>
```

checker は次を別 finding として検出する。

- index 内または全モデル横断の duplicate ID
- path 脱出、欠損、読取不能
- row と record の ID / type / revision / canonical hash 不一致
- directory に存在するが index にない orphan record
- index にあるが schema registry で許可されない record type

orphan は advisory では warning、strict では error とする。index 不一致と hash 不一致は常に error とする。

## Research Model

Research Model は既存 CLM / RES / FIG / SRC / GATE identity を維持する。本文 prose や raw artifact をコピーせず、card が表す研究判断を typed field として保持する。

### claim

- statement、scope、limitation、not_claiming
- evidence/result/source/figure refs
- visual obligation refs、manuscript block refs
- warrant と assumptions
- `gate_status`、`human_approval`
- validation history と approval history

status は `draft / proposed / validated / approved / rejected / superseded`。本文で使用する claim は `approved` で、現在 revision/hash に対する `scientific_scope` approval を必要とする。

### result

- observation、estimand、unit_of_analysis、denominator、independence_risk
- comparison、metrics、quantity contracts
- source/artifact provenance の public identifier
- claim/figure/block refs、scope、limitation、route

quantity contract は QTY ID、value、denominator、unit、estimand、aggregation、independence、source artifact ID、block refs を保持する。絶対 path、raw data、実行 host は field に持たない。

### figure

- reader task、takeaway、claim/decision、encoding、scale/denominator
- uncertainty、caption scope、accessibility、acceptance criteria
- result/claim/block/visual obligation refs
- manuscript role、design review、audit checks、route

### source

- source kind、citation keys、verification state、promotion decision
- claim boundary、parameter choice、reviewer objection、method precedent
- claim/block refs と public provenance reference

credential need や raw capture の絶対 location は model へ入れず、必要なら local/confidential state の opaque ID だけを `extensions` に置く。

### scientific_gate

- claim ID、gate decision、required checks、blocking issue/request refs
- central assumptions、stress tests、external validation gates
- approved writing scope、not covered、history

gate decision は `draft / ready_to_write / analysis_needed / assumption_blocked / supplement_only / deferred`。`ready_to_write` は対象 claim の現在 revision/hash と一致する `scientific_scope` approval を要求する。

## Manuscript Model

Manuscript Model は prose の正本ではない。section/block 構造、対応言語、参照、compile state を保持し、`manuscript/ja` と `manuscript/en` の TeX は引き続き human-edited authority とする。

### section

- kind: `abstract / introduction / methods / results / discussion / conclusion / supplement`
- ordered block IDs
- section state: `unplanned / planned / compiled / drafted / verified / stale`
- contract refs、Editorial move refs、Research refs
- source-of-truth language と mirror policy
- compiled manifest reference、dependency hash、last verified dependency hash

### block

- section ID、position、block kind、reader task、operation
- JA / EN TeX block ID
- approved claim/result/source/figure refs、citation keys
- `compiled_from` に compiler version、schema versions、input IDs/hashes
- dependency hash、last verified dependency hash
- allowed operation と forbidden scope expansion

`operation` は post-draft review の `keep / compress / move / merge / split / cut / rewrite`、Editorial Model の pre-draft `stance` は `assert / reject / boundary / hold` として別に保持する。

同じ section 内の block position は1始まりで欠番を許さない。JA / EN pair を要求する project profile では対応 block ID を両方必須にする。P1-B schema は pair field を持つが、TeX 実在と mirror ledger の厳密検査は既存 checker を維持し、P3 compiler で統合する。

`compiled_from` が存在する block は、参照する claim が approved、gate が ready-to-write、dependency hash が current でなければならない。未承認 claim は `approval.missing`、gate 不足は `semantic.claim_not_writable`、dependency 差分は `dependency.stale` と別々に報告する。

## Issue Model

Issue Model は feedback / request / response を一つの issue envelope に潰さず、共通 envelope と typed payload を持つ per-ID record とする。raw confidential reviewer text は追跡せず、公開可能な summary と local raw reference の有無だけを保持する。

共通 field:

- source、severity、route、targets、review round
- confidentiality: `public / internal_summary / confidential_local_only`
- status、closure criteria、blocking dependencies
- related issue/card/block refs

record type:

- `feedback`: issue type、upstream routes、route explanation、delegation metadata
- `analysis_request`: planned analysis、prediction、replacement、runops handoff、execution provenance、reconciliation
- `writing_request`: target blocks、claim/evidence constraints、mirror policy
- `response`: feedback refs、resolution routes、closure audit、changed refs
- `review_round`: scope、artifact refs、feedback set、delegation ledger、integration decisions

analysis request status は既存の `planned / predicted / running / executed / reconciled / abandoned` を保持する。`executed` は artifact/result/figure refs、`reconciled` は reconciliation と human signoff を要求する。predicted result が manuscript/publication dependency に残る場合は `semantic.predicted_unresolved` とする。

response の `closed` は closure criteria が満たされ、open analysis request、未承認 scope change、human decision が残らない場合だけ許す。原稿変更だけで closure を推論しない。

## Publication Model

Publication Model は living authoring axis と submission axis を分離する。

- venue と requirements profile
- authoring state
- current mutable candidate
- append-only round ledger
- source commit、gate report、submitted artifacts、review round、response package
- snapshot manifest と参照 object revision/hash
- submission approval history

candidate status は `candidate / gated / revision_candidate`。round status は `frozen / submitted / under_review / resubmitted / accepted / rejected / withdrawn`。`submitted` 以降の round は immutable とし、内容変更は同じ round の revision ではなく新 round IDを作る。

schema だけでは過去 file との差分を判断できないため、P1-B checker は次を検査する。

- round ID、snapshot path、source commit、artifact refs の必須性
- current round の実在と status 整合
- round ID と snapshot path の重複
- submission approval が current candidate hash と一致すること
- snapshot dependency に predicted/unreconciled request、未承認 claim、stale block がないこと

実ファイルの immutable enforcement と snapshot 作成は P4/P7 で実装する。P1-B は `immutability.required` finding と manifest contract を提供する。

## 全モデル横断 reference graph

checker は schema phase が成功した document だけから ID catalog を作る。per-ID record に加え、Editorial の story/move/visual obligation と Results hierarchy item を virtual object として登録し、subrecord JSON Pointer から object-level canonical hash を計算する。これらは独立 revision を持たず、hashだけで dependency snapshot を固定する。ID prefix だけで実在を推測しない。参照 field ごとに許可 target type と cardinality を schema companion metadata で固定する。

主要 edge:

```text
Editorial claim role / move / visual obligation
  -> Research claim / result / figure
Manuscript section / block
  -> Editorial move / Results item / Research records
Issue feedback / request / response / round
  -> Research / Editorial / Manuscript / Issue records
Publication candidate / round
  -> Manuscript section/block, Issue review/response, Research approvals
```

finding を次のように分離する。

- `reference.duplicate`: stable ID が全 catalog で重複
- `reference.dangling`: target ID が存在しない
- `reference.type`: target は存在するが許可 type でない
- `reference.cardinality`: 必須本数または一意性違反
- `approval.missing`: current object への必要 approval がない
- `approval.stale`: approval の revision/hash が過去値
- `dependency.stale`: dependency snapshot が target current value と違う
- `semantic.predicted_unresolved`: predicted/unreconciled research request が公開対象へ流入

P1-A の claim/figure `reference.deferred` は、対応 Research records が registry に登録された時点で実在確認へ切り替える。results hierarchy の local document binding は維持する。

## dependency hash profile

profile 名を `dependency-v1` とする。入力は対象 object の dependency entries を current catalog へ解決して作る。

```json
{
  "profile": "dependency-v1",
  "dependencies": [
    {
      "target_id": "RES-0001",
      "relation": "supported_by",
      "revision": 2,
      "hash": "sha256:..."
    }
  ]
}
```

- entries は `(target_id, relation)` の Unicode code point 順で整列する。
- JSON serialization と SHA-256 表現は `semantic-v1` と同じ規則を使う。
- dependency が持つ timestamp、path、generated text は target canonical hash の除外規則に従い、直接入力しない。
- hash は `sha256:<64 lowercase hex>`。
- dependency graph の cycle は `dependency.cycle` とし、hashを部分生成しない。
- `--print-dependency-hash <ID>` は schema/reference/approval error がなく、全 target hash を解決できる場合だけ出力する。

record の `last_verified_dependency_hash` と current dependency hash が違う場合は `dependency.stale`。同じであれば timestamp が変わっても stale にしない。

## extension と schema upgrade

- schema 未定義 field は拒否し、拡張は `extensions` 内の `x-<owner>-<name>` だけ許す。
- extension は既定で semantic hash に含める。
- PaperOps が extension を理解しない場合でも JSON互換性、key形式、duplicate/non-finite は検査し、値を捨てない。
- registry/document の未知 schema version は error。新 version へ自動 coercion しない。
- schema upgrade は新 schema file と migration ID を追加し、旧 version の reader horizon を registry に明記する。
- managed update は schema を追加できるが project-owned record を書き換えない。
- migration が未知 extension を変換できない場合は conflict report に残し、部分適用しない。

## Registry の拡張

P1-A registry に `record_sets`、`reference_contract`、`dependency_profile` を追加する。旧 aggregate entry はそのまま読める。

```yaml
research:
  document_kind: index
  schema: research-index.schema.json
  default_path: _paperops/model/research/index.yml
  record_sets:
    claim:
      schema: research-claim.schema.json
      path_prefix: _paperops/model/research/claims/
      id_pattern: ^CLM-[0-9]{4,}$
      hash_excluded_paths:
        - /metadata/updated_at
  dependency_profile: dependency-v1
```

registry definition error は P1-A 互換の正式 code `registry.*` として停止し、project document finding とは混ぜない。P1-A の exact model-set test は P1-B の six-entry contract（五論理モデル + Results hierarchy submodel）へ更新する。

## CLI と gate

`check-paperops-models.py` を次へ拡張する。

```text
python scripts/check-paperops-models.py --root . --model research --phase all
python scripts/check-paperops-models.py --root . --all-models --strict
python scripts/check-paperops-models.py --root . --print-hash --object-id CLM-0001
python scripts/check-paperops-models.py --root . --print-dependency-hash BLK-0001
```

phase は `schema / references / semantics / approvals / dependencies / hash / all`。schema error がある record は後続 phase から除外し、catalog へ不完全な object を登録しない。

`make schema-check` は全モデル advisory を既定とする。P1-B 完了時点でも `finish` / `pre-submit` の authority は既存 card/workflow なので、新モデル strict gate へはまだ切り替えない。P2 shadow compare と P4 workflow migration 後に public gate へ昇格する。

## Fixture と回帰

P1-A の三つの合成 editorial fixture を拡張し、各 case に四モデルの index/record/publication file を追加する。

- mechanism-led: approved claim、result、figure、source、gate、compiled block、closed issue、candidate
- boundary-led: boundary claim、scope-limited gate、boundary move、staleでない dependency
- negative-result-led: reconciled negative request、rejected alternative、negative result、response closure

invalid corpus は最低限次を個別 mutation で持つ。

- duplicate ID
- invalid status
- dangling target
- wrong target type
- unapproved claim used by compiled block
- stale approval
- stale dependency revision
- stale dependency hash
- dependency cycle
- orphan record
- unresolved predicted result in publication
- closed response with open request
- mutable submitted round contract violation
- unknown extension outside `extensions`
- unknown schema version

同じ semantic record は mapping順、comment、line endingに関係なく同じ canonical/dependency hashになり、claim scope、move order、block dependency、round snapshot参照の変更で該当 hash が変わることをテストする。

## 移行・互換性

P1-B は `M0-0005` を guide-only migration として登録する。既存 project には四モデルの starter/indexを自動配置せず、次の順だけを案内する。

1. managed schema/checker を update する。
2. project-owned model tree を別作業領域で作る。
3. legacy card/workflow/ledger と件数・ID・status・参照を照合する。
4. `schema-check --strict` と cross-reference/dependency check を通す。
5. P2 の shadow mode が利用可能になるまでは legacy-authoritative を維持する。

新規 `pops init` は空 index と publication starter を配置する。legacy cards、workflow、submission ledger はP4/P7まで残り、P1-B model と二重の writable authority にしない。P1-B model starter は opt-in typed state で、legacy-authoritative 中は checker対象でも workflow writer対象ではない。

ユーザー向け interface 変更として README、AGENTS/CLAUDE、CLI docs、migration guide、skill catalog、disposition、CHANGELOG を同じ変更単位で更新する。

## 受入条件

- Research / Manuscript / Issue / Publication の managed schema と project starter がある。
- 全 record family の existing field disposition が文書化され、既存 card/workflow/ledger の情報を黙って落とさない。
- duplicate ID、不正 status、dangling/wrong-type reference、未承認 claim、stale approval、stale dependency を別 code で検出する。
- object canonical hash と dependency-v1 hash が安定し、意味変更だけで変化する。
- submitted snapshot と living manuscript の authority が混ざらない。
- P1-A の三 fixture が全モデルを横断して strict validation を通る。
- project-owned state は managed update で上書きされない。
- migration note と CHANGELOG があり、`make smoke` が計算ノードで通る。
- P2/P3/P4 の未提供機能を提供済みと文書化しない。
