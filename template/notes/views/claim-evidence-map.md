# 主張と証拠のビュー

このファイルは `claims/claims/`、`claims/gates/`、`evidence/` のカードを人間が俯瞰するためのビューである。claim の正本は claim card に置く。

## 中心主張

未記入。読者に持ち帰ってほしい中心主張を 1 文で書く。可能なら title candidate と同じ方向の主張にする。

## 主要結果

1. 未記入 - 中心主張を支える - 図表:
2. 未記入 - 中心主張を支える - 図表:
3. 未記入 - 代替説明を退ける - 図表:

## 主張台帳

| 主張ID | card | 主張 | 証拠 | 論拠・推論 | 適用範囲 | 限界 | 本文ブロック | 図表 | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-0001 | `claims/claims/CLM-0001.md` | 未記入 | RES-0001 / SRC-0001 | 未記入 | 未記入 | 未記入 | 未記入 | FIG-0001 | draft |

`supported` に昇格する前に、中心主張は対応する gate card でも `ready-to-write` になっているか確認する。`analysis-needed` や `assumption-blocked` の主張は Abstract / Conclusion / main figure caption に使わない。

## Result pattern 由来の evidence

| 主張ID | pattern ID | packet ID | evidence card | evidence role | warrant | scope / limitation | 本文ブロック |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-0001 | RP-0001 | EP-0001 | RES-0001 | core evidence / mechanism / boundary / robustness / negative control | 未記入 | 未記入 | 未記入 |

## 主張しないこと

- 本論文では主張しないことを記録する。
- 将来課題、補足、別論文へ送ることを記録する。

## 条件・ケースの論文上の役割

| 条件グループ | ローカル証拠 | 論文上の文脈 | claim role | scope statement | 条件数を書く場所 |
| --- | --- | --- | --- | --- | --- |
| 未記入 | 未記入 | 未記入 | core evidence / mechanism / boundary / robustness / negative control / exploratory | 未記入 | 本文 / 図注 / Methods / supplement / notes |

## 主張強度の調整

- `draft`: まだ仮説または作業中の主張。
- `supported`: evidence と warrant が揃い、本文で明確に主張してよい。
- `overclaim risk`: evidence より強く見えるため、scope または limitation の調整が必要。
- `defer`: 本文の中心主張には入れず、将来課題または補足に回す。

## Scientific gate との対応

| 主張ID | gate card | gate status | block reason | approved writing scope | next route |
| --- | --- | --- | --- | --- | --- |
| CLM-0001 | `claims/gates/GATE-0001.md` | ready-to-write / analysis-needed / assumption-blocked / supplement-only / defer | 未記入 | 未記入 | `/scientific-gate` / `/map-result-patterns` / `/research-related-work` |
