# 結果パターンビュー

このファイルは `evidence/results/` と `evidence/figures/` のカードを人間が俯瞰するためのビューである。result の正本は result card / figure card に置く。

## 結果パターン inventory

| pattern ID | card ID | raw result / artifact | observed contrast | effect direction / magnitude | condition groups | negative or null cases | uncertainty / failure mode | candidate interpretation | candidate claim role | next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RP-0001 | RES-0001 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | core evidence / mechanism / boundary / robustness / negative control / exploratory / provenance-only | keep / merge / split / defer / discard |

## 観察から解釈への変換

| pattern ID | 観察された事実 | そのまま書くと弱い表現 | 論文上の意味 | 本文で主語にするもの | 関連する figure/table |
| --- | --- | --- | --- | --- | --- |
| RP-0001 | 未記入 | 未記入 | 未記入 | 未記入 | FIG-0001 |

## Evidence packet 化する場合

| packet ID | pattern ID | result card | supported claim ID | figure/table | metric | scope | limitation | manuscript block | reproduce / provenance link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EP-0001 | RP-0001 | RES-0001 | CLM-0001 / 未定 | FIG-0001 | 未記入 | 未記入 | 未記入 | 未記入 | `notes/reproducibility.md` / supplement / `refs/links.toml` |

## Claim に昇格する前の確認

- result card の estimand、unit of analysis、denominator、provenance が埋まっているか。
- observed contrast は、単なる run inventory ではなく、読者に意味のある比較になっているか。
- negative or null cases は、失敗、境界条件、negative control、不十分な coverage のどれかに分類されているか。
- candidate interpretation は、データより強く言いすぎていないか。
- 条件名、case count、denominator は `notes/views/condition-context-map.md` で公開文脈へ翻訳されているか。
- claim に昇格する場合、`claims/claims/` の claim card と `claims/gates/` の gate card に接続できるか。

## 本文へ入れない provenance

- raw run label
- scheduler log
- internal export name
- local directory
- script name
- 全条件の inventory
- 主張に寄与しない screening

## 未解決の結果パターン

- 未記入
