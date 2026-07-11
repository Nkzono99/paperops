# ADR 0001: Authority・ownership・物理配置

- Status: Accepted
- Decision ID: ADR-0001
- Parent: [RFC 0001: PaperOps 2](../rfcs/0001-paperops-2.md)

## Context

PaperOps 2 は複数の論理モデルを導入するが、それらを五つの巨大 YAML に固定すると、競合範囲、writer ownership、部分 migration の影響が大きくなる。一方、分割だけを目的に細粒度化すると、一覧性と検証可能性を失う。managed default、論文固有の typed state、人間が編集する原稿、生成 cache、機密な local state、publication snapshot を同じ更新規則で扱うこともできない。

必要なのは、論理モデルと物理ファイルを一対一に固定することではなく、一つの判断に対して writable な正本と writer を一つに限定し、managed update と project editing が互いの所有領域を侵さない配置である。

## Decision

論理モデルごとに **per-ID record + index** を第一候補とする。record は安定 ID を持ち、index は discovery と順序付けに使う。小規模で競合範囲が明確なモデルには小さな集約 file を許容するが、巨大 YAML を既定にはしない。

各 record または集約 file は authority class と唯一の writer を持つ。同じ判断を表す複数 representation が存在しても writable authority は一つだけとし、他は read-only view、compatibility alias、または generated cache とする。index は record の内容を別の正本として複製しない。

managed pattern は project-owned path を包含してはならない。migration は authority の切替を明示し、検証完了前に旧正本を削除しない。

human-edited manuscript source について、Writer は patch を生成するだけとする。human が patch の採否を承認し、承認済み patch は human または将来の deterministic applicator が適用する。Writer は manuscript authority へ直接書き込まない。

## Ownership table

| Authority class | 内容 | 所有者 / writer | tracked | 更新規則 |
|---|---|---|---|---|
| paperops-managed default | schema、prompt default、contract、starter | PaperOps release / managed update | yes | versioned update。project-owned typed state を上書きしない |
| project-owned typed state | story、claim、evidence、issue、publication metadata の論文固有 record | project workflow ごとに指定された単一 writer | yes | explicit command または approved migration のみ |
| human-edited manuscript source | TeX、対応する人間編集 source | human、または将来の deterministic applicator | yes | human が採否を承認した patch だけを適用し、Writer の直接書込みを許可しない |
| generated cache | compiled packet、judge output、materialized view | deterministic compiler / checker | no | authority から再生成し、正本として読まない |
| local/confidential state | credential、絶対 path、raw reviewer text、未公開 raw data | local user / external system | no | tracked model へコピーしない |
| immutable publication snapshot | submission 時点の原稿、manifest、参照 revision | publication snapshot command | yes | 作成後は変更せず、新 submission は新 snapshot とする |

## Physical layout

次を規範的な形とし、具体的な basename と schema version は各モデルの実装 ADR で固定する。

```text
_paperops/
  defaults/                 # paperops-managed default
  contracts/                # paperops-managed default
project-state/
  <model>/
    index.yaml              # ID、順序、参照の索引
    records/
      <stable-id>.yaml      # per-ID record
.paperops-cache/            # generated cache、未追跡
local-state/                # local/confidential state、未追跡
snapshots/
  <submission-id>/          # immutable publication snapshot
manuscript/                 # human-edited manuscript source
```

小規模モデルでは `project-state/<model>.yaml` のような集約 file を選べる。ただし、各判断の ID、revision、writer が識別可能で、同じ内容を records と集約 file の双方から更新できないことを条件とする。実際の下流 path は disposition と migration 設計を経て決め、この例だけで既存 path を移動しない。

## Consequences

- ID 単位の review、revision、selective stale、atomic replacement が可能になる。
- managed default と project state の所有境界を path と checker の双方で検証できる。
- index と record の参照整合性検査が必要になる。
- 多数の小ファイルを扱う保守コストが生じるため、競合しない小規模モデルには集約 file を許す。
- compatibility representation には read-only または generated であることを明示する必要がある。

## Revisit conditions

- 同一判断に複数の writable authority または writer が見つかった場合。
- managed update が project-owned typed state を上書きし得る場合。
- per-ID record の運用コストが評価 fixture の decision density や review 性を継続的に悪化させる場合。
- local/confidential state が tracked path に混入する場合。
- immutable snapshot を living manuscript の更新が変更できる場合。
