# RFC 0001: PaperOps 2

- Status: Accepted for staged implementation
- Scope: template governance and downstream scaffold evolution

## 問題

現行 PaperOps では、論文固有の判断、テンプレート既定値、原稿、生成物、ローカル情報の境界が artifact ごとに異なる。inventory 型の構成は存在する項目を列挙できても、なぜその story、claim、argument move を選んだかを十分な密度で保持できない。また、CLI、Agent、compiler、Writer の責務が明文化されなければ、同じ判断に複数の writable な正本が生じ、managed update や migration が project-owned state を壊し得る。

PaperOps 2 はこの問題を、既存の下流リポジトリを一度に置き換えず、authority と writer を先に固定してから段階的に解く。

## 目標

- Research、Editorial、Manuscript、Issue、Publication の論理モデル間のデータフローを明示する。
- paperops-managed default と project-owned typed state を分離し、一つの判断に一つの writable な正本を割り当てる。
- deterministic な機械処理と editorial choice を分離し、承認済み情報だけを原稿執筆へ渡す。
- 旧新 pipeline を同一 fixture で比較できる移行経路を設け、検証成功前に旧正本を削除しない。
- living manuscript と immutable publication snapshot を分離する。

## 非目標

- この RFC で五つの論理モデルの schema、canonical hash algorithm、typed compiler、本文 patcher を実装すること。
- この段階で legacy artifact、skill、checker を削除すること。
- Agent の editorial judgment を deterministic CLI の内部へ取り込むこと。
- raw reviewer text、credential、絶対 path、未公開 raw data を tracked state に保存すること。

## 論理モデル

PaperOps 2 の基本フローは次のとおりとする。

```text
Research Model
  -> Editorial Model
  -> compiled Writer packet
  -> reviewable manuscript patch
  -> human approval / deterministic application
  -> Manuscript Model / TeX authoring source
  -> Issue Model feedback loop
  -> Publication Model snapshot
```

Research Model は観測、根拠、quantity、figure、citation を扱う。Editorial Model は story candidate、選択・棄却理由、claim role、argument move を扱う。Manuscript Model は living manuscript の構造と authoring intent を扱う。Issue Model は review と修正要求を循環させる。Publication Model は特定時点の submission を immutable snapshot として固定する。物理配置と所有権は [ADR 0001](../adr/0001-authority-ownership-layout.md) に従う。

## Authority と writer

schema、prompt default、managed contract は paperops-managed default とし、論文固有の typed model state は project-owned typed state とする。TeX と対応する human-edited manuscript source は human が編集する。Writer は patch を生成するだけで、human が採否を承認し、承認済み patch は human または将来の deterministic applicator が適用する。Writer が tracked authority へ直接書き込むことは禁止する。compiled Writer packet、judge output、materialized view は再生成可能な cache とし、tracked authority にしない。

同一判断の writable な正本は常に一つとする。各 rollout phase で active writer を一つに限定し、非 authoritative pipeline は比較用の読み取りまたは隔離された shadow output の生成だけを行う。責務境界は [ADR 0002](../adr/0002-cli-agent-compiler-boundary.md)、revision と stale 判定の入力境界は [ADR 0003](../adr/0003-revision-state-hash.md) に従う。

## 成功指標

- inventory 型構成より decision density が改善し、story candidate の選択理由、棄却理由、claim role、argument move を追跡できる。
- mechanism-led、boundary-led、negative-result-led の同一 fixture で旧新比較を行い、構造・判断・生成 packet の差分を説明できる。
- JA/EN mirror、block ID、quantity、figure、citation、authoring intent など既存 strict check を失わない。
- migration conflict 時に部分更新しない。旧正本、v2 state、index、derived output が混在した中間状態を残さず、検証前の状態へ戻せる。
- predicted result と analysis request の lifecycle、claim・move・block 単位の selective stale、living manuscript と immutable snapshot の分離を維持する。
- managed update が project-owned state を上書きしないことを自動検査できる。

## 撤退条件

次のいずれかが再現した段階では v2-authoritative への昇格を停止し、直前の authoritative pipeline へ戻す。

- 同じ判断の authority が二重化し、二つ以上の writer が正本を更新できる。
- private/raw 情報が tracked state へ混入する。対象には raw reviewer text、credential、絶対 path、未公開 raw data を含む。
- 同一 fixture による主要評価が旧 pipeline より悪化し、decision density、strict check、selective stale、または追跡可能性を回復できない。
- migration の復元手順が成立しない、または conflict 時に部分更新が残る。

撤退時は新規 writer を停止し、直前 phase の正本を唯一の writable authority に戻す。shadow output と cache は破棄可能でなければならない。

## 段階導入

### legacy-authoritative

legacy artifact が唯一の writable authority である。v2 側は schema、fixture、migration preflight を開発できるが、project state や原稿を更新しない。旧 checker の結果を基準値として保存する。

### shadow

legacy writer を唯一の authority としたまま、v2 adapter/compiler が隔離された未追跡 output を生成する。shadow は legacy state、v2 state、原稿を更新しない。同一 fixture の旧新比較、strict check、decision density、hash 入力候補を評価する。

### opt-in v2-authoritative

明示的に opt-in した下流リポジトリだけで v2 state を唯一の writable authority とする。migration は preflight、atomic write、post-validation、rollback を備え、成功後も legacy representation は read-only compatibility view または復元点として保持する。legacy writer は暗黙起動しない。

### default v2-authoritative

成功指標を満たし撤退条件に該当しないことを fixture と opt-in project で確認した後、新規 project の既定を v2-authoritative にする。既存 project は明示 migration まで legacy-authoritative のままとし、managed update だけで authority を切り替えない。

### legacy removal

全 tracked project の migration 経路、互換 alias、復元手順が検証され、旧 reader/writer の利用が観測されなくなった後にのみ個別に判断する。削除は disposition と release note を伴う別変更とし、この RFC の採択だけでは実施しない。

## 互換 invariant

- JA/EN mirror と block ID を維持する。
- quantity、figure、citation、authoring intent の deterministic check を維持する。
- predicted result と analysis request の lifecycle を維持する。
- claim、move、block 単位の selective stale を失わない。
- living manuscript と immutable submission snapshot を分離する。
- paperops-managed default と project-owned state の境界を維持し、managed update で project-owned state を上書きしない。
- migration validation が成功する前に legacy deletion を行わず、競合時は部分更新せず conflict stop とする。
- strict、advisory、diagnostic、starter の意味を混同しない。
- raw reviewer text、credential、absolute path、unpublished raw data、generated cache は tracked state に含めない。
- malformed typed state が存在する場合、legacy state へ暗黙 fallback してエラーを隠さない。

## 評価

実研究の未公開原稿や raw data を含まない三つの合成 fixture を用いる。mechanism-led は主機構の立証と代替説明の棄却、boundary-led は成立条件と破綻境界、negative-result-led は不成立結果からの仮説または測定限界の更新を評価する。

各 fixture は二つ以上の story candidate、選択理由、棄却理由、Results hierarchy、claim role、argument move を持つ。旧新 pipeline へ同一 input を与え、decision density、既存 checker の結果、packet の限定性、selective stale、migration の atomicity と rollback を比較する。将来 single-candidate profile を評価する場合は `single_candidate_reason` を必須とする。

## 関連判断

- [ADR 0001: Authority・ownership・物理配置](../adr/0001-authority-ownership-layout.md)
- [ADR 0002: CLI・Agent・compiler 境界](../adr/0002-cli-agent-compiler-boundary.md)
- [ADR 0003: Revision・state・hash](../adr/0003-revision-state-hash.md)
- 現行 artifact の retain / adapt / redirect / deprecate / remove / investigate は [Disposition matrix](../paperops2-disposition.md) で管理する。
