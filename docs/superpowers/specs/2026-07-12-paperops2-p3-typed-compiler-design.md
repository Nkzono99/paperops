# PaperOps 2 P3 Typed Compiler / Writer Boundary 設計

## 位置づけ

P3は、P2でmodel単位に採用可能になったResearch、Editorial、Results hierarchy、Manuscript stateから、検証可能なsection planとWriter packetを決定的に生成し、AI Writerがcandidate TeXを直接推敲できる隔離環境と、承認済み差分だけをhuman-edited TeXへ反映するtransactionを提供する。

P3は意味論的な構成を一度固定して局所Writerへ閉じ込める段階ではない。AIは原稿全体とglobal storyを読み、上位構成の再検討を提案できる。一方、CLIが暗黙にeditorial choiceを行ったり、AIがtracked authorityへ直接書き込んだりしない。

P4はP3のcompile/write eventを使い、model revision、Issue、approval、selective stale、macro-state projectionのwriterを実装する。P3だけではP2のmodel authority modeやtracked workflow stateを変更しない。

## 目標

- Editorial Modelのselected story、reader transformation、claim roles、argument movesを全sectionのpre-draft planへ接続する。
- AIが全体の意味と現在のTeXを読める`read_context`と、今回変更可能な`write_scope`を分離する。
- Writerが隔離candidate workspaceではTeXを直接・反復編集し、buildや全体通読を行えるようにする。
- 同一inputからbyte-identicalなcompile bundleを生成する。
- Writer変更をbase hash、block marker、scope、claim/evidence conservationで検査する。
- 人間の明示承認後だけ、対象TeXをsnapshot付きtransactionで更新する。
- 上位storyやsection構成を新revisionで再検討でき、既存compile outputを永続lockにしない。
- JA/EN mirror、quantity、figure、citation、predicted-result、privacy、既存Make profileの意味を失わない。

## 非目標

- CLI内部からAI、network、model、API keyを呼ぶこと。
- AIの意味論評価を決定的なpass/failで代替すること。
- P3 compiler実行時にEditorial / Manuscript Model、P2 authority mode、workflow stateを暗黙更新すること。
- P4のmacro state、multi-issue routing、revision writer、approval ledgerを先取りすること。
- legacy writer、existing checker、section compiler skillを削除すること。
- v2 pipelineを新規projectのdefault writerにすること。
- submission candidateやimmutable submitted snapshotをWriter candidate workspaceとして再利用すること。

## 基本原則

### 改訂可能な階層

P3は次の階層を持つが、上から下への不可逆pipelineにはしない。

```text
Editorial Model revision
  selected story / reader transformation / claim roles / argument moves
      ↓ dependency
Manuscript section revision
  section role / contract / move placement / ordered block IDs
      ↓ dependency
Manuscript block revision
  reader task / operation / claim-result-figure refs / forbidden expansion
      ↓ compile
Writer packet + candidate TeX
      ↓ semantic review / escalation
new Editorial, section, or block revision proposal
```

prose reviewでglobal storyの問題を見つけた場合、局所patchへ押し込まず、candidateを破棄して上位revision proposalへ戻る。承認済みrevisionもsupersede可能であり、「compiled」は構成を将来変更できないlockを意味しない。

### Read contextとwrite scope

Writer packetは読める範囲と変更できる範囲を別fieldで持つ。

- `read_context`はglobal semantic synopsis、原稿全体、前後section、contract、terminology、citation allowlist、mirror stateを含められる。
- `write_scope`は対象language、file、section ID、block ID、許可operationを列挙する。
- Writerはcandidate workspaceの全原稿を読める。対象外を編集した場合、`pops write check`がscope violationとして拒否する。
- 全体再構成では、人間が明示した`manuscript` scopeを使う。通常の局所修正を黙って全体scopeへ拡大しない。

### 機械的正しさと意味論評価

決定的checkerは次だけをblockingにする。

- schema / reference / revision / dependency / authority drift
- claim、quantity、figure、citation、argument moveの未説明な消失
- staleまたは未承認Research input
- block marker、mirror pair、scope、base TeX hashの不一致
- private/raw material、absolute path、credentialのpacket混入
- 部分生成、部分適用、manual edit上書き

thesis recoverability、reader shift、section間の論理、primary resultの順位、alternative story、narrative weightはAgent / humanが評価する。P3は比較材料と差分を生成するが、semantic judgeを通常CLIのblocking gateにしない。

## Authorityとownership

| Artifact | 配置 | ownership | writer |
| --- | --- | --- | --- |
| Research / Editorial / Results / Manuscript Model | `_paperops/model/` | project-owned typed authority | P3ではread-only。P4の明示revision writerまで変更しない |
| managed schema / section contract | `_paperops/defaults/` | paperops-managed | `pops update-paperops` |
| project contract overlay / writing profile | `_paperops/contracts/`, `manuscript/writing-profile.yml` | project-owned | human / approved Agent workflow |
| compile bundle / Writer packet | `.paperops/compile/<compile-id>/` | ignored generated cache | deterministic compiler |
| Writer candidate workspace | `.paperops/writer/<session-id>/workspace/` | ignored candidate | scoped AI Writer / human |
| patch / report / journal | `.paperops/writer/<session-id>/` | ignored CLI state | deterministic CLI |
| rollback snapshot | `.paperops/snapshots/<transaction-id>/` | ignored CLI state | deterministic CLI |
| living TeX | `manuscript/ja/`, `manuscript/en/` | human-edited manuscript authority | human、または明示承認後のapplicator |
| submission snapshot | `submission/` | publication artifact | P3は変更しない |

generated cacheが失われてもtracked authorityの意味は変わらない。cacheが存在しない場合、CLIはreceiptを捏造せず、同じauthority inputから再compileする。

## Input sourceとauthority mode

compilerはinput sourceを明示する。

- `authoritative`: Research、Editorial、Results hierarchy、ManuscriptがP2の`v2-authoritative`で、latest authority journalとcurrent hashが整合する場合だけ使用できる。
- `shadow`: 指定したP2 shadow transactionのcandidateをread-only評価する。compile bundleとcandidate TeXは作れるが、tracked TeXへの`write apply`は禁止する。
- legacy inputをP3 compilerが直接推測変換しない。legacy-only projectはP2 adapterを経由する。
- malformed typed stateが存在する場合、legacy fallbackで隠さない。

P3は`pops model adopt`を暗黙実行しない。shadowでalternative storyを比較し、人間判断後に別commandでmodel adoption / revisionへ進む。

## Authoritative planの再利用

新しい構成正本は増やさない。

- Global storyは既存Editorial Modelの`revision`、`reader_transformation`、`story_candidates`、`selected_story_id`、`claim_roles`、`argument_moves`を使う。
- Section plan authorityはManuscript section recordの`revision`、`section_kind`、`ordered_block_ids`、`contract_refs`、`editorial_move_refs`、`research_refs`を使う。
- Block plan authorityはManuscript block recordの`reader_task`、`operation`、`allowed_operations`、`claim_refs`、`result_refs`、`source_refs`、`figure_refs`、`citation_keys`、`forbidden_scope_expansion`を使う。
- generated `section-plan.json`はこれらのvalidated projectionであり、別のwritable authorityではない。

selected storyが参照するargument moveはsectionの`editorial_move_refs`へ配置する。compilerはmove coverage、section順、block coverageを報告する。primary placementと意図的なechoを区別できない現行fieldについては、P3 schemaを追加的に拡張し、section側にmove binding roleと理由を持たせる。既存`editorial_move_refs`は互換projectionとして残す。

## Approval boundary

Research claimはcurrent `scientific_scope` approvalと`ready_to_write` gateを既存checkerで要求する。

Editorial Model自体には独立approval historyがないため、P3はselected statusだけをhuman approvalと見なさない。authoritative compileでは次をすべて要求する。

1. P2 adoption transactionとcurrent Editorial / Results / Manuscript hashが一致する。
2. 対象Manuscript section/blockが参照するstory/move/claim/result hashをdependenciesへ含む。
3. 対象section planにcurrent `editorial_choice` approvalが存在する。
4. `manuscript` scopeでは全対象section planが同じcurrent Editorial snapshotへ承認済みである。

P3 applyの人間承認はpatch hash、compile ID、write scope、base TeX hashへ結び付けてjournalに記録する。P3はこのoperation approvalからtracked model approval recordを合成しない。P4がmodel revision / approval authorityを導入した後、同じeventをtyped approvalへ接続する。

## Compiler products

compile IDはcompiler contract versionと全input snapshotのcanonical hashから決める。同じinputとtarget/scopeなら同じIDとbyte列になる。timestamp、host、cache pathをhashへ含めない。

```text
.paperops/compile/<compile-id>/
  bundle.json
  report.json
  context/
    global.json
  plans/
    <SEC-ID>.json
  packets/
    <packet-id>.json
```

### `bundle.json`

- schema / compiler contract version
- `authoritative`または`shadow` source
- model authority mode、model hash、transaction ID
- target section/blockとwrite scope
-全input manifestとdependency profile/hash
- packet / plan pathとcontent hash
- validation result

### `context/global.json`

- reader transformation
- selected / rejected storyと理由
- thesis、claim role、evidence ladder
- ordered argument moves
- section / block map
- primary / supporting / supplement / cutのsalience
- visual obligation、terminology、mirror policy
-全原稿のproject-relative read pathとcontent hash

全文TeXはcandidate workspaceに存在するため、global contextへ重複保存しない。

### `section-plan.json`

- section ID / revision / semantic hash / section kind
- reader question、section purpose、前後sectionとの接続
- ordered block IDsとargument move placement
- contract default、project overlay、writing profileのresolved snapshot
- Research / Editorial / Results input refs
- missing function / evidence / definition blocker

Resultsは`reader_question → answer → quantitative evidence → figure → baseline rationale → scope → consequence`を保持する。Discussionはobservation / inference / mechanism / alternative / implication / prediction / limitationとprincipal findingからdecisive next testまでを保持する。Methodsはestimand、unit、baseline、criterion、verificationとmain/supplement/citation/code placementを保持する。

### Writer packet

```text
packet identity/version
compiler version and compile ID
authority snapshot
target section/block IDs and current hashes
read_context paths/hashes and global semantic synopsis ref
write_scope language/files/block IDs/allowed operations
inputs[] as one object per ID/revision/hash/type/relation
dependency profile/hash
selected story, moves, approved claims and evidence
quantity / figure / source / citation refs
resolved contract/profile snapshot
mirror policy and terminology rules
forbidden assertions and scope expansion
predicted-result mode and AREQ refs when explicitly enabled
```

parallelな`input_ids` / `input_hashes`だけをpacket authorityにしない。各inputを一objectへ束ね、catalog objectとcatalog外inputを区別する。

## Dependency coverage

packetへ入る全inputは、次のいずれかに必ず現れる。

- catalog object: model、object type、ID、revision（存在する場合）、semantic hash、relation
- non-catalog snapshot: project-relative identity、contract/profile version、canonical content hash

対象にはsection/block dependenciesだけでなく、Editorial move、Results item、claim/result/source/figure、section contract、project overlay、writing profile、citation registry、terminology、mirror map、TeX block preimage、予測稿を許可するlegacy analysis-request cardのcontent snapshotを含む。citation registryは既存checkerと同じ `manuscript/shared/bib/*.bib`、`_paperops/refs/bib/imported/*.bib`、`_paperops/refs/bib/curated/*.bib` のproject-relative identity、content hash、sorted entry keyだけをsafe snapshot化し、raw BibTeX本文はglobal contextやWriter packetへ複製しない。

P3のauthoritative model入力はResearch、Editorial、Results hierarchy、Manuscriptの4 modelに限定する。予測稿のopen AREQ状態は、既存workflowとの互換bridgeとして `_paperops/requests/analysis/*.md` のfrontmatterから `{id,status,identity,content_hash}` だけをsafe snapshot化して判定し、raw request本文をWriter-facing contextへ複製しない。typed Issue authorityへのcutoverはP4で扱う。

timestamp、absolute path、実行host、credentialをdependency materialへ入れない。入力追加・削除・hash変更は関係するpacketだけをstaleにする。

## Public CLI

定型操作を次の二入口へ集約する。

```text
pops compile status [target|all] [path] [--json]
pops compile prepare <target|all> [path] [--scope block|section|manuscript]
                     [--block <BLK-ID> ...] [--shadow <transaction-id>]
                     [--refresh] [--json]
pops compile compare <compile-id-a> <compile-id-b> [path] [--json]

pops write start <compile-id> [path] [--json]
pops write status <session-id> [path] [--json]
pops write check <session-id> [path] [--json]
pops write diff <session-id> [path] [--json]
pops write apply <session-id> [path] --yes [--json]
pops write rollback <transaction-id> [path] [--json]
```

`compile`と`write`はAIを起動しない。skill / Agentは`write start`後のcandidate workspaceを編集する。human outputとJSON outputは同じdomain resultを描画する。

## Candidate workspace

`pops write start`はliving manuscriptの全体copyとcompile bundleを`.paperops/writer/<session-id>/workspace/`へ作る。WriterはこのcopyのTeXを直接編集し、必要なら複数回build / reviewできる。

- 全原稿を読むことを許可する。
- write scope外のfile/block変更はcheckで拒否する。
- preamble、shared style、bibliography、figure binaryは明示scopeなしに変更できない。
- candidate workspaceは`submission/`ではなく、投稿roundを作らない。
- Writerがglobal/section問題を発見した場合は`replan_required`としてreportし、scopeを自動拡張しない。

write scopeは三段階とする。

- `block`: 明示block集合だけを変更する。通常の局所修正。
- `section`: current Manuscript Modelが計画済みの一section内block追加・削除・順序変更をmaterializeできる。
- `manuscript`: current Manuscript Modelが計画済みの複数section再構成をmaterializeできる。全対象section plan approvalと明示人間選択を要求する。

candidateでmodel未記載のblock追加・削除・移動を試すことはできるが、checkは`replan_required`としてauthoritative applyを止める。Global Architect / Section Editorが上位model revisionを提案し、そのrevisionがcurrentになって再compileされた後だけ、新しいtopologyをapplyできる。P3がcandidate差分からManuscript Modelを逆生成しない。

## Patch validation

`pops write check/diff`はcandidateとbaseからversioned patch manifestを作る。

- file / block preimage hash
- replacement content hash
- added / removed / moved block marker
- requested operationとallowed operation
- changed languageとmirror impact
- preserved / moved / removed claim、quantity、figure、citation、move disposition
- scope violationとmanual base drift
- existing deterministic checker result

TeX本文の意味同一性をCLIが断定しない。ID/reference conservationは機械検査し、thesis、reader flow、salience、alternative storyはGlobal Architect / Section Editor / human reviewへ渡す。

## Apply transactionとrollback

`pops write apply --yes`はapply直前にcompile bundle、candidate、base TeX、current authority hash、scope、checkerを再検証する。shadow compileからのapplyは禁止する。

対象fileをsnapshotし、journalを`planned → validated → snapshotted → replacing → committed`でatomicに更新する。複数language/fileのapplyは一transactionとし、failure時に部分更新を残さない。unknown manual edit、snapshot corruption、base driftはconflict stopする。

P3 applyはliving TeXだけを更新し、Editorial / Manuscript Model、workflow state、mirror freshness ledgerを暗黙更新しない。compile/write receiptはignored CLI stateに保持する。P4がrevision writerを導入した後、TeX applyとtyped model transitionを同じ上位transactionへ接続する。

rollbackは既知post-apply hashの場合だけsnapshotを復元し、適用後の人間編集があれば停止する。

## JA / EN mirror

- `% block:` markerの集合、順序、重複を既存`mirror-check`とP3 scope checkerの両方で検査する。
- `ja_tex_block_id` / `en_tex_block_id`とlegacy `% block:` identityを暗黙に同一視せず、明示bindingをcompile inputに持つ。
- paired scopeで両言語を変更する場合は同一transactionにする。
- 片言語だけ変更する場合は許可するが、対側をcurrent扱いにせずfreshness driftを報告する。
- `block-ledger.yml`のsync hashはsemantic/dependency hashに流用しない。
- compiler/applicatorはledgerの`--update`を自動実行しない。review済み同期後の明示操作を維持する。

## Existing skill / checker bridge

- `finish-manuscript`は薄いrouteのまま維持する。
- `compile-results-section`、`compile-discussion-section`、`compile-methods-section`はP3 CLIを使うleafへ更新し、旧名を削除しない。
- global reviewは既存`design-paper-storyline`をGlobal Architectとして拡張する。
- post-draft `review-block-flow`は残し、局所prose問題をsection/global replanへescalateできるようにする。
- `.agents`を正本、`.claude`をwrapperとして同時更新する。
- existing `make ci`、`audit`、`finish-manuscript-check`、`pre-submit`のstrict/advisory semanticsを黙って変えない。
- P3 checkerは既存mirror、section contract/depth、block-flow、citation、quantity、figure、claim-evidence、authoring-intent checkerを置換せず、同等性確認まで追加gateとして使う。

legacy block-flowの`delete`はtyped `cut`へprojectionし、legacy `add`は新block proposalへprojectionする。typed canonical operationは`keep / compress / move / merge / split / cut / rewrite / add`とし、既存enumへ`add`だけを追加する。legacy viewでは`cut`を`delete`として表示できる。

P3はlegacy uppercase workflow section stateとtyped Manuscript lowercase statusをread-only bridgeで読むが、どちらも書き換えない。state authority cutoverはP4で行う。

## Privacyとpublic language

- packet/candidate reportにraw reviewer text、credential、absolute path、unpublished raw dataを保存しない。
- project-relative pathはCLI internal identityとして扱い、Writer-facing public prose materialへ混ぜない。
- public URL、DOI、citation key、公開software名は保持する。
- terminologyの`internal_only` / `forbidden`はWriter packetの禁止範囲へ入れる。
- predicted materialは明示mode、open AREQ、required markerがある場合だけauthoring candidateへ入れ、observed evidenceと混同しない。submission treeへは適用しない。

## Alternative storyと全体再評価

`pops compile compare`は二bundle間のselected story、move順、claim role、result order、section placement、figure obligation、write scopeの構造差分を決定的に出す。どちらが良いかは判断しない。

Global Architectは全原稿、global context、比較reportを読み、次をproposalする。

- current revisionを維持
- block / section revisionへ戻る
- Editorial Modelのnew revisionへ戻る
- alternative storyを再評価
- primary / supporting / supplement / cutのsalienceを変更

上位変更を選んだ場合、current compile bundleとWriter sessionはstaleになり、再compileする。過去bundleは比較可能だがauthorityにはならない。

## Failure semantics

findingはversioned code、JSON Pointer、project-relative identityを持つ。traceback、absolute path、private valueをpublic outputへ出さない。

主なblocking code family:

- `compile.authority_*`
- `compile.approval_*`
- `compile.dependency_*`
- `compile.coverage_*`
- `compile.contract_*`
- `compile.privacy_*`
- `write.scope_*`
- `write.base_*`
- `write.mirror_*`
- `write.conservation_*`
- `write.transaction_*`
- `write.recovery_conflict`

failure時は成功bundle、partial packet、partial TeX、partial model/workflow updateを残さない。diagnostic reportだけをignored transaction directoryへ保存できる。

## Fixtureと評価

少なくとも次の合成fixtureを持つ。

1. approved typed computational manuscript
2. mechanism-led / boundary-led / negative-result-led全story
3. deterministic compileとtracked no-mutation
4. approval / stale / dangling / wrong-typeのsingle mutation corpus
5. default contract + project overlay + writing profile merge
6. Results / Discussion / Methods semantics
7. exact JA/EN pair、single-language drift、duplicate / reorder
8. block-flow operation bridge
9. legacy / typed presenceとmalformed typed no-fallback
10. private/public-language boundary
11. block / section / manuscript write scope violation
12. manual TeX edit conflict、atomic multi-file apply、rollback
13. alternative story bundle compareと上位revision escalation
14. existing Make gate equivalence
15. source treeとbuilt-wheel CLI

compileの反復はbyte-identicalで、failure時のtracked treeはbyte単位で不変とする。candidate編集後もapply前はtracked TeX、model、workflow、mirror ledgerを変更しない。

## Rollout

P3は追加導入とする。

- 新規・既存projectともP3 commandは明示実行だけ。
- P2 authority modeを自動昇格しない。
- legacy compiler skillとhuman direct editingを削除しない。
- shadow compileとauthoritative compileの比較を先に行う。
- default writer cutover、legacy writer停止、removal versionはP7で判断する。
- schema、scripts、skills、AGENTS / CLAUDE、README、CLI docs、migration note、CHANGELOGを同時更新する。

## P4への出力契約

P4はP3の次の構造化eventを利用する。

- compile ID、authority snapshot、input dependency set
- target section/blockとwrite scope
- bundle status、stale reason、replan target level
- Writer session / patch hash / operation approval
- apply / rollback transaction result
- changed block IDs、claim/result/figure/citation disposition
- mirror impact

P4はこれをmodel revision、individual Issue、approval record、selective stale、macro-state projectionへ接続する。P3 event自体をtracked workflow authorityとして扱わない。

## 受入条件

- AIは全原稿とglobal semanticsを読め、candidate workspaceでTeXを直接反復編集できる。
- local write scopeが全体理解を制限せず、scope外変更だけを機械的に拒否する。
- global / section / block revisionへいつでも戻れ、compile済み状態が意味論的lockにならない。
- 未検証・未承認・stale inputからauthoritative packetを生成しない。
- 同一inputのbundleがbyte-identicalである。
- tracked authorityをcompile/start/check/diffで変更しない。
- manual TeX editやscope driftを上書きせず停止する。
- apply / rollbackがatomicで、unknown edit時にconflict stopする。
- claim、quantity、figure、citation、argument moveの未説明な消失を検出する。
- JA/EN mirrorと片言語freshnessを失わない。
- semantic qualityをdeterministic gateへ偽装せず、alternative story比較と上位escalationを維持する。
- P4未実装のmodel/workflow writerをP3が暗黙代行しない。
