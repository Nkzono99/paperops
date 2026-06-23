# 結果パターン台帳

simulation results、figure data、analysis artifact、run output を、本文の主張へ直接流し込まず、まず論文上の観察単位へ束ねるための中間層。

このファイルでは、まだ claim ではない result pattern を扱う。主張として採用するものは `notes/claim-evidence-map.md`、条件名や denominator の翻訳は `notes/condition-context-map.md`、論文全体の読み筋は `notes/argument-map.md` に分けて記録する。

## 結果パターン inventory

| pattern ID | raw result / figure-data / run reference | observed contrast | effect direction / magnitude | condition groups | negative or null cases | uncertainty / failure mode | candidate interpretation | candidate claim role | next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RP-0001 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | core evidence / mechanism / boundary / robustness / negative control / exploratory / provenance-only | keep / merge / split / defer / discard |

## 観察から解釈への変換

| pattern ID | 観察された事実 | そのまま書くと弱い表現 | 論文上の意味 | 本文で主語にするもの | 関連する figure/table |
| --- | --- | --- | --- | --- | --- |
| RP-0001 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 |

## Evidence packet 化する場合

1 pattern が 1 つの result story として本文や図表に入る場合、以下を埋める。

| packet ID | pattern ID | supported claim ID | figure/table | metric | scope | limitation | manuscript block | reproduce / provenance link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EP-0001 | RP-0001 | C1 / 未定 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | `notes/reproducibility.md` / supplement / `refs/links.toml` |

## Claim に昇格する前の確認

- observed contrast は、単なる run inventory ではなく、読者に意味のある比較になっているか。
- effect direction / magnitude は、図表や表で確認できるか。
- negative or null cases は、失敗、境界条件、negative control、不十分な coverage のどれかに分類されているか。
- candidate interpretation は、データより強く言いすぎていないか。
- 条件名、case count、denominator は `notes/condition-context-map.md` で公開文脈へ翻訳されているか。
- claim に昇格する場合、`notes/claim-evidence-map.md` に evidence、warrant、scope、limitation を移せるか。

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
