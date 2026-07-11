# PaperOps 2 P2: Deterministic model migration and intuitive CLI

## 目的

P1-Bで追加した六モデルを、AI agentに定型作業をさせずに既存projectへ安全に採用できるようにする。利用者はlegacy card、index、hash、snapshot、transaction journalを直接操作せず、`pops model`の高水準commandから状態確認、検証、差分、採用、rollbackを行う。

P2はmodel stateの移行境界を提供する。section compiler / Writer packetはP3、workflow writer cutoverはP4、public skill/gateの全面整理はP5で扱う。P2完了だけでlegacy writerを停止したり、legacy artifactを削除したりしない。

## 検討した方式

### 採用: model単位の状態機械とtransaction

各model authorityを`legacy-authoritative`、`shadow-compare`、`v2-authoritative`の三状態で管理する。移行はmodel単位で行い、依存modelを検査する。失敗や未変換fieldを局所化でき、model単位でrollbackできるため採用する。

### 不採用: 六モデル一括cutover

PublicationやIssueの未解決状態がResearch採用まで止め、rollback範囲も過大になる。project全体を一度に置換する方式は採用しない。

### 不採用: shadow-only

差分reportだけではauthorityを安全に切り替える経路がなく、手動file操作が再び必要になる。shadow生成を終点にはしない。

## 公開CLI

公開入口は次の五つに固定する。

```text
pops model status [MODEL|--all] [--json]
pops model validate [MODEL|--all] [--strict] [--json]
pops model diff MODEL [--refresh] [--json]
pops model adopt MODEL [--dry-run] [--yes] [--json]
pops model rollback MODEL [--to TRANSACTION_ID] [--cascade] [--dry-run] [--yes] [--json]
```

- `MODEL`は`research`、`editorial`、`results_hierarchy`、`manuscript`、`issue`、`publication`のいずれかとする。
- `status`はauthority mode、current hash、last shadow transaction、blocking dependency、recoverable transactionを表示する。
- `validate`はproject側のmanaged `check-paperops-models.py --json`をshell文字列ではなく固定argvで起動し、同じphase順とfindingを返す。project schema/checker versionとCLI package versionが一致しない場合は更新案内を出して停止する。
- `diff`は必要ならshadow candidateを再生成し、legacy inventoryとcandidateのconservation reportを表示する。project-owned / tracked modelは変更しないが、persistent shadowが作成された場合はCLI-owned manifestのmodeとshadow transaction metadataをatomicに更新する。
- `adopt`はshadow生成、strict検証、conflict検査、snapshot、置換、manifest更新を一つのrecoverable transactionとして実行する。
- `rollback`はsnapshotのhashを検証してから復元する。v2-authoritativeなdependent modelがある場合は停止し、`--cascade`が指定された場合だけ依存逆順で同一transactionへ含める。
- 通常成功はexit 0、検証・変換・conflictによる停止はexit 1、CLI usage errorはexit 2とする。
- `--json`は同じ結果をversioned objectとして返し、human outputをparser contractにしない。

既存`pops migrate list/show/apply`はlayout migrationと低水準互換入口として残す。model adoptionを行う新しいmigration IDは増やさず、M0-0005はguide-onlyのままとする。

## authority state

authority stateはCLI-ownedの`.pops/manifest.toml`に保存する。

```toml
[models.research]
mode = "shadow-compare"
current_hash = "sha256:..."
last_shadow_transaction = "model-20260711T120000Z-abc123"
last_adopt_transaction = ""

[models.editorial]
mode = "legacy-authoritative"
current_hash = ""
last_shadow_transaction = ""
last_adopt_transaction = ""
```

- 六model entryを常に書く。
- 未記録の既存projectは全modelを`legacy-authoritative`として読む。
- `results_hierarchy`は独立entryを持つが、`editorial`採用時はcompanionとして同一transactionに含める。
- manifestはproject-owned model内容を複製せず、modeとtransaction/hashだけを持つ。
- `pops update-paperops`によるscaffold version更新は既存`[models.*]`を保持する。
- `v2-authoritative`なのにmodelが欠損または記録hashと不一致、`shadow-compare`なのにshadow transactionが欠損する場合、CLIは`state.inconsistent`で停止し、暗黙修復しない。`legacy-authoritative`でstarterや未採用typed fileが存在すること自体は許可する。

## dependency-aware adoption

採用dependencyは次で固定する。

```text
results_hierarchy ─┐
                   ├─ editorial
research ──────────┼─ manuscript
research ──────────┼─ issue
research ──────────┐
manuscript ────────┼─ publication
issue ─────────────┘
```

- `editorial`はResults hierarchyを同時に採用する。
- `manuscript`はResearchが少なくともshadow candidateとしてstrict-cleanであることを要求し、Editorial / Results hierarchy参照を持つ場合はそれらもcandidate catalogで解決する。
- `issue`は参照するResearch / Editorial / Manuscript objectがcandidate catalogで解決できることを要求する。
- `publication`はResearch、Manuscript、Issueがv2-authoritativeであることを要求する。
- rollbackは逆dependencyを検査する。dependentがv2-authoritativeなら通常は停止し、`--cascade`だけが逆topological orderで対象を広げる。

## deterministic adapter

adapterはmodelごとに独立moduleとし、次のinterfaceを実装する。

```python
@dataclass(frozen=True)
class MigrationInput:
    root: Path
    model_name: str
    source_paths: tuple[Path, ...]

@dataclass(frozen=True)
class MigrationCandidate:
    model_name: str
    documents: tuple[CandidateDocument, ...]
    inventory: tuple[InventoryItem, ...]
    findings: tuple[MigrationFinding, ...]

class ModelAdapter(Protocol):
    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]: ...
    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate: ...
```

adapterはnetwork、AI model、LLM prompt、GitHub APIを利用しない。Markdown front matter、既存table、YAML/TOML、file identityから決定できる値だけを写す。解釈が必要なfieldは空文字や架空値で埋めず、`migration.unresolved` findingとsource pointerをreportする。unknown fieldは`migration.unknown_field`、同一legacy IDの競合は`migration.duplicate`、private/raw値は`migration.confidential`とする。

model別入力は次で固定する。

- Research: `_paperops/claims/claims/`、scientific gate、result / figure / source card。
- Editorial: `_paperops/notes/views/storyline.md`、typed Results hierarchy、argument / visual obligation card。Results hierarchyは既存typed fileを検証し、legacy Markdownだけの場合は構造化rowをcandidateへ変換する。
- Manuscript: section contract、block ID、mirror ledger、TeX structure。prose本文はmodelへコピーしない。
- Issue: feedback、analysis request、writing request、response、review round card。raw reviewer textはcandidateへ入れず、public summaryとopaque local referenceだけを扱う。
- Publication: submission ledger、candidate manifest、round snapshot manifest。submitted artifact自体は移動せず参照とhashだけをmodelへ写す。

adapterが完全変換できないことは正常な結果である。`diff`はblocking gapを表示し、利用者がlegacy authority側またはproject-owned candidateを直して再実行できるようにする。AI agentによる穴埋めを推奨手順にしない。

## staging、report、snapshot

生成物はtracked stateへ直接書かない。

```text
.paperops/
  migrations/<transaction-id>/
    journal.json
    candidate/_paperops/model/**
    report.json
    report.md
  snapshots/<transaction-id>/
    manifest.json
    _paperops/model/**
```

- `.paperops/`は既存除外規則のままGit管理しない。
- `transaction-id`はUTC timestampとrandom suffixから作り、path-safeかつ一意にする。
- `report.json`を正本、`report.md`をhuman-readable projectionとする。
- reportはadapter version、schema version、source relative path/hash、candidate object ID/hash、field disposition、finding code/pointer/severityを持つ。
- absolute path、credential、raw reviewer text、file content全文をreportへ保存しない。
- snapshot manifestはrelative path、file mode、sha256を持つ。symlink、path escape、special fileは拒否する。

## transactionとcrash recovery

複数pathとmanifestを単一filesystem primitiveだけで同時置換できないため、durable journalとrecoverable commit protocolを使う。

1. `planned`: input inventoryとtarget setを固定する。
2. `materialized`: stagingへcandidateとreportを書き、全fileをflushする。
3. `validated`: schema / references / semantics / approvals / dependencies / hashとconservation gateが成功する。
4. `snapshotted`:置換対象の既存stateとmanifest hashをsnapshotへ保存する。
5. `replacing`: target directoryを同一filesystem上の`os.replace`で切り替える。
6. `committed`: temporary manifestを`os.replace`し、mode/hash/transactionを更新する。

各step前後にjournalをtemporary file + `os.replace`で更新する。`committed`以外のjournalを検出した`pops model` commandは通常処理を開始せず、次を行う。

- targetが旧hashならstagingを破棄して`rolled_back`へ進める。
- targetがcandidate hashでmanifestが旧hashならsnapshotから旧targetを復元する。
- target/manifestが既知hashのどれとも一致しない場合は`recovery.conflict`で停止し、人間の選択なしに上書きしない。

`--dry-run`はinventory、candidate、reportを一時directory内で計算しても、projectの`.paperops/`、model state、manifestをbyte単位で変更しない。通常`diff`はpersistent shadow transactionを作り、manifestを`shadow-compare`へ進めてよいがproject-owned / tracked modelとlegacy authority fileは変更しない。

## conservation gate

schema-cleanだけではlegacy情報の欠落を検出できないため、adapter inventoryとcandidate inventoryを比較する。

- legacy IDはcandidate IDまたは明示`deferred / local-only / unsupported` dispositionを一つだけ持つ。
- claim scope、quantity denominator / unit / estimand、figure obligation、source provenance、review closure、submission roundは必須conservation familyとする。
- `unsupported`はadopt blocker、`deferred`は理由と後続phaseを要求し、`local-only`はconfidential情報だけに許可する。
- source hashがshadow生成後に変わった場合は`migration.source_changed`でadoptを停止する。
- candidate fileがshadow生成後に手編集された場合は`migration.candidate_changed`で停止し、`diff --refresh`で再生成する。

## Python component boundary

P1-Bで`paperops_models.py`が大きくなったため、migration logicを同fileへ追加しない。

```text
src/paperops/cli/model_commands.py       CLI parse/render only
src/paperops/model_state.py              manifest model-state read/write
src/paperops/model_migration/types.py    immutable DTOs and finding codes
src/paperops/model_migration/adapters/   one adapter per model
src/paperops/model_migration/catalog.py  legacy inventory and conservation
src/paperops/model_migration/staging.py  safe paths, reports, snapshots
src/paperops/model_migration/transaction.py journal and recovery protocol
src/paperops/model_validation.py         safe argv/JSON invocation of project checker
```

CLI renderingはdomain objectを変更せず、`--json`とhuman outputが同じresultから作られるようにする。adapter、transaction、validationはCLI parserをimportしない。

## error policy

finding codeはprefixで責務を分ける。

- `migration.*`: source inventory、field conversion、conservation。
- `transaction.*`: snapshot、replace、journal、source/candidate drift。
- `recovery.*`: interrupted transactionの整合。
- `state.*`: authority modeとmanifest/model fileの矛盾。
- P1-Bの`schema.*`、`reference.*`、`semantic.*`、`approval.*`、`dependency.*`、`immutability.*`は変換せずそのまま伝播する。

CLIはtracebackを通常出力へ漏らさず、finding code、project-relative pointer、actionable messageを返す。`--json`のschema versionは1から開始する。

## testing

通常testとsmokeは外部APIなしで再現する。

- unit: model state default/preservation、adapter mapping、unknown/duplicate/private data、safe path、inventory conservation、dependency order。
- transaction: dry-run byte identity、conflict before mutation、source drift、candidate drift、各journal stepでのcrash injection、recovery rollback、repeat no-op。
- CLI: five public commands、human/JSON parity、exit 0/1/2、unknown model、non-project invocation。
- migration fixtures: legacy-only、typed-only、mixed、modified managed、existing project-owned state、partial missing、unknown field、submitted round。
- rollback: single model、blocked dependent、explicit cascade、snapshot corruption、manual target edit。
- distribution: source treeとbuilt wheelの`pops model status/diff/validate`。
- regression: mirror、session notes、legacy readers、managed update、`pops init`、all P1-B fixtures。

KUDPC login nodeではtest payloadを直接実行せず、host/module/spartition/qgroupを確認して`tssrun`または`sbatch`経由で実行する。

## documentationと互換性

- `pops model`をREADME、CLI guide、architecture、current specification、template interfacesへ追加する。
- M0-0005はguide-onlyのまま、P2 CLI adoption手順への入口として更新する。
- `CHANGELOG.md`に既存projectのmodel stateを自動上書きしないこと、rollback、legacy authority維持を記載する。
- `pops migrate`、legacy checker、legacy writer、legacy cardは削除しない。
- `template/AGENTS.md`、`template/CLAUDE.md`、`template/scripts/`の変更にはmigration noteを付ける。

## 完了条件

- AI / networkなしで六モデルのstatus、validate、diff、adopt、rollbackが実行できる。
- dry-run、validation failure、conflictではtracked projectとmanifestがbyte単位で変わらない。
- interrupted transactionは既知snapshotへ復元でき、未知の手編集を上書きしない。
- legacy field familyはcandidateまたは明示dispositionへ一対一で保存される。
- modelごとのauthority modeとdependencyが一貫し、Publicationの早すぎるcutoverを拒否する。
- managed updateはproject-owned model、shadow candidate、snapshotを上書きしない。
- P2完了後もP3 / P4未完了のlegacy writerとTeX authorityを維持する。
