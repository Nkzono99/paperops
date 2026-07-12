---
view_type: pure_overview
starter_example_rows: true
source_of_truth:
  - _paperops/model/research/gates/
authoritative_for:
  - overview
---

# Claim Upgrade Gates View

このファイルは external validation needs、claim stress-test、observational boundary など、claim を強める前に止める gate を俯瞰するビューである。正本は `_paperops/model/research/gates/` の scientific gate card と、必要な `_paperops/model/issues/analysis/` / `_paperops/model/issues/responses/` のカードに置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## Upgrade gate matrix

| gate ID | claim component | gate type | source artifact | blocking claim | allowed wording | must-not-claim | validated scope | not covered | route | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UPG-0001 | 未記入 | external-validation / claim-stress / observational-boundary / authoring-guard | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | research-request / limitation / response-matrix / defer | open |

## Guard

- external validation row は claim support ではなく claim upgrade blocker として扱う。
- claim stress-test は physical evidence ではなく allowed wording と must-not-claim を固定する authoring gate として扱う。
- `tracked=true`、`ready=1`、`non_consistent_rows=0` などの green metric があっても、allowed next action と forbidden next action を併記する。
- Abstract / Conclusion / Key Points / main caption へ進める前に、該当 claim component の upgrade gate が開いたままではないか確認する。
