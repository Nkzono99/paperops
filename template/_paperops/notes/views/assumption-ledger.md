---
view_type: pure_overview
starter_example_rows: true
source_of_truth:
  - _paperops/model/research/gates/
authoritative_for:
  - overview
---

# Assumption Ledger View

このファイルは `_paperops/model/research/gates/` の central_assumptions を人間が俯瞰するためのビューである。正本は gate card と関連する claim / evidence / request card に置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## Assumption matrix

| assumption ID | assumption name | guarded claims | artifact role | evidence / source | solved | not solved | upper/lower-bound role | manuscript placement | status | required follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ASM-0001 | 未記入 | CLM-0001 | measured model / validated solver output / proxy / sensitivity / authoring guard | 未記入 | 未記入 | 未記入 | upper / lower / bracket / none | main / supplement / limitation / future work | supported / proxy / sensitivity / unresolved | 未記入 |

## Guard

- `proxy` / `sensitivity` / `authoring guard` は claim support ではなく、limitation、future work、または analysis request へ route する。
- probability-like column がある場合は、denominator と生成過程が自然確率か sensitivity grid かを書く。
- `measured model` や `validated solver output` ではない artifact を、Abstract / Conclusion / main caption の強い claim に使わない。
