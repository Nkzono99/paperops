# PaperOps 2 P0-A 設計基盤

## 目的

PaperOps 2 の大規模再設計を、既存の下流リポジトリを壊さず段階的に進めるため、実装前に正本、所有権、責務境界、状態、互換条件、評価方法を固定する。

このサイクルでは GitHub Issue を作らない。設計判断の正本はこのリポジトリ内の RFC、ADR、disposition matrix とし、必要になった時点でそれらを参照して Issue や release planning へ展開する。

## スコープ

このサイクルで行うこと:

1. 直前に完了した typed Results hierarchy の実績を `_handoff/TODO.md` に反映する。
2. typed Results hierarchy が壊れた YAML であっても legacy Markdown へ暗黙 fallback しない回帰テストを追加する。
3. PaperOps 2 全体 RFC を作成する。
4. 設計判断を三つの ADR 群へ分離する。
5. 現行 artifact、skill、checker、Make target の disposition matrix を作成する。
6. mechanism-led、boundary-led、negative-result-led の三つの合成 editorial fixture の要件を定義する。

このサイクルでは行わないこと:

- 五つの論理モデル全体の schema 実装
- shadow adapter、atomic migration、canonical hash の実装
- typed compiler、Writer packet、本文 patcher の実装
- workflow state、Issue Model、approval record の切替
- legacy artifact、skill、checker の削除
- release、push、外部 Issue 作成

## 成果物の分割

### RFC

PaperOps 2 全体の目的、問題設定、成功指標、撤退条件、段階導入順序、互換方針を記述する。個別の構造選択を重複して詳述せず、対応する ADR と disposition matrix を参照する索引としても機能させる。

### ADR 1: 正本・所有権・物理配置

次の区分を固定する。

- paperops-managed default
- project-owned typed state
- human-edited manuscript source
- generated cache
- local/confidential state
- immutable publication snapshot

論理モデルを五つの巨大 YAML に固定しない。per-ID record と index、または小さな集約ファイルをモデルごとに選択できる。ただし、一つの判断に writable な正本は一つだけとする。

### ADR 2: CLI・Agent・compiler の責務境界

`pops` CLI は deterministic な検証、移行、materialization、状態表示を担当する。Agent と skill は editorial choice、代替案比較、文章判断を担当する。compiler は承認済み typed input から限定された Writer packet を生成し、Agent の判断を CLI 内で暗黙実行しない。

### ADR 3: revision・state・canonical hash

UI の macro state、object revision、section state、review round、submission axis を分離する。canonical hash と dependency hash は将来の実装要件として入力境界と除外対象を定義するが、このサイクルではアルゴリズムを実装しない。

### Disposition matrix

ルート層と `template/` 層を分け、現行 artifact、skill、checker、Make target ごとに以下を記録する。

- 現在の責務
- 論理モデルまたはgateとの対応
- `retain / adapt / redirect / deprecate / remove`
- 移行前後のwriterとreader
- 互換aliasまたはmigrationの要否
- 削除判断の条件

未調査項目は disposition を空欄にせず `investigate` と理由を記録する。`remove` はこのサイクルでは実行しない。

## データフローと正本

```text
Research Model
  -> Editorial Model
  -> compiled Writer packet
  -> Manuscript Model / TeX authoring source
  -> Issue Model feedback loop
  -> Publication Model snapshot
```

schema とprompt defaultはpaperops-managed、論文固有のmodel stateはproject-owned、compile packetとjudge outputは未追跡cacheとする。raw reviewer text、credential、絶対path、未公開raw dataはtracked modelへ入れない。

typed Results hierarchy はこの原則の先行実装として扱う。managed schemaとproject-owned stateを分離し、typed fileが存在する場合は不完全でもlegacyへfallbackしない。

## 互換条件

次を非交渉のinvariantとする。

- JA/EN mirrorとblock IDを維持する。
- quantity、figure、citation、authoring intentのdeterministic checkを維持する。
- predicted resultとanalysis requestのlifecycleを維持する。
- claim、move、block単位のselective staleを失わない。
- living manuscriptとimmutable submission snapshotを分離する。
- project-owned stateをmanaged updateで上書きしない。
- migrationは明示的で、検証成功前に旧正本を削除しない。
- strict、advisory、diagnostic、starterの意味を混同しない。

## 評価fixture

三件とも合成データを使用し、実研究の未公開原稿やraw dataを含めない。

1. mechanism-led: 主機構を順に立証し、代替説明を棄却する構成。
2. boundary-led: 成立条件と破綻境界を中心に、一般化範囲を制限する構成。
3. negative-result-led: 予想した効果が現れない結果から、仮説または測定限界を更新する構成。

各fixtureは最低二つのstory candidate、選択理由、棄却理由、Results hierarchy、claim role、argument moveを持つ。単一候補を許す将来profileを検証する場合は `single_candidate_reason` を要求する。

このサイクルではfixtureの仕様と保存場所を確定する。具体的なschema fixtureはP1の最初の実装計画で追加する。

## エラーと停止条件

- dispositionが判断不能な項目は推測せず `investigate` と根拠を残す。
- 同じ判断に複数のwritableな正本が見つかった場合はP1へ進まず、authority ADRを修正する。
- project-owned stateをmanaged patternが包含する場合は回帰として扱う。
- malformed typed stateをlegacyで隠す挙動はerrorとする。
- RFC、ADR、matrix間で用語やauthorityが矛盾した場合はコミット前に解消する。

## テスト方針

- malformed typed YAMLの専用回帰テストはREDを確認してから、必要な最小修正だけを行う。
- 設計文書について、必須成果物、invariant、root/template分離、disposition語彙を検査するdocumentation regression testを追加する。
- `_handoff/TODO.md` は追跡対象外の作業台帳として更新し、コードの受入判定には使わない。
- `template/` のcheckerまたはtestを変更するため、最後にKUDPC計算ノード上で `make smoke` を実行する。

## 完了条件

- P0-Bの完了項目と残件がTODO上で区別されている。
- malformed typed YAMLのno-fallbackが自動テストで固定されている。
- RFC、三つのADR、disposition matrixが相互参照されている。
- root層と`template/`層の変更対象がmatrixで区別されている。
- 成功指標、撤退条件、shadow/cutover時のwriterがRFCまたはADRに明記されている。
- 三つの合成fixtureの目的と必須要素が固定されている。
- `make smoke` が成功する。
