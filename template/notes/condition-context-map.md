# 条件文脈マップ

simulation condition、case count、run inventory を、そのまま本文の主張にせず、論文上の意味へ翻訳するための台帳。

## 条件軸の公開名

| 条件軸 | 公開名 | 読者に伝える意味 | 代表するもの | 代表しないもの |
| --- | --- | --- | --- | --- |
| 未記入 | 未記入 | 未記入 | 未記入 | 未記入 |

## Local condition から paper context への対応

| local ID / count | 公開条件名 | 条件軸 | claim role | denominator の意味 | 本文での言い方 | 図表 | notes-only provenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 未記入 | 未記入 | 未記入 | core evidence / mechanism / boundary / robustness / negative control / exploratory / provenance-only | 未記入 | 未記入 | 未記入 | 未記入 |

## 条件の役割

- `core evidence`: 中心主張を直接支える。
- `mechanism`: 何が効いているかを説明する。
- `boundary`: 主張が成立しない範囲や破れる条件を示す。
- `robustness`: 主張が設定変更に対して残ることを示す。
- `negative control`: 対照として、主張の必要条件を示す。
- `exploratory`: 本文では弱く扱い、今後の検証候補にする。
- `provenance-only`: 本文には出さず、再現性や補足へ退避する。

## 本文で言ってよい形

- 「12 条件中 2 条件で見えた」ではなく、「特定の保持条件を満たす境界条件で効果が現れ、同じ条件軸を欠く対照では再現しなかった」と書く。
- 「8 条件中 0 条件」は単なる失敗ではなく、negative evidence、boundary、insufficient coverage のどれかに分類する。
- 条件数は主語にしない。物理条件、選別基準、機構、境界条件を主語にする。

## 本文から退避する形

- run inventory
- 条件番号の全列挙
- denominator の内部定義
- scheduler log、raw output directory、未整理の export 名
- 主張に寄与しない screening 結果

## 未解決の条件文脈

- 未記入
