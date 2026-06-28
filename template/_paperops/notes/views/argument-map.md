---
view_type: controlled_authoring
starter_example_rows: true
source_of_truth:
  - _paperops/claims/arguments/
  - _paperops/claims/claims/
  - _paperops/evidence/
authoritative_for:
  - manuscript_argument_order
  - reader_path
---

# 論旨設計ビュー

このファイルは `_paperops/claims/arguments/` の argument card を人間が俯瞰するためのビューである。論旨構造の正本は argument card に置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## 一文の中心主張

未記入。

## 証拠の階層

| layer | claim / evidence card | reader job | manuscript location |
| --- | --- | --- | --- |
| core evidence | CLM-0001 / RES-0001 | 中心主張を支える | 未記入 |
| boundary | 未記入 | 射程を決める | 未記入 |
| robustness | 未記入 | 代替説明を弱める | 未記入 |
| negative control | 未記入 | not claiming を明確にする | 未記入 |

## ローカル条件から公開主張への抽象化

- raw condition count:
- paper context:
- public wording:
- route:

## 概念語と普通の文への展開

強い英語名詞句や hyphen / slash compound は `_paperops/notes/views/concept-terms.md` に記録し、本文で強調語として残すか、普通の文へほどくかを決める。

- accepted concept term:
- plain-language expansion:
- avoid / unstable wording:

## Defense budget

防御的 caveat、not claiming、limitation を本文のどこに置くかを決める。

## Reader path

- intro:
- method:
- result:
- discussion:
- conclusion:
