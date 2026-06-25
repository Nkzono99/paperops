---
id: RES-0001
type: result
status: draft
source_refs: []
artifact_refs: []
unit_of_analysis: ""
estimand: ""
metrics: []
quantity_contracts: []
comparison: ""
depends_on: []
claim_links: []
figure_links: []
manuscript_blocks: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Result Card

## 観察

解析結果、simulation result、figure data から読める観察を書く。raw run label やローカルパスを本文用の表現にしない。

## 推定対象と単位

- estimand:
- unit of analysis:
- denominator:
- independence risk:

## Quantity contracts

本文、Abstract、Conclusion、table、caption に出す count / fraction / maximum は、必要に応じて `quantity_contracts` に機械可読で登録する。

```yaml
quantity_contracts:
  - id: QTY-0001
    value: ""
    denominator: ""
    unit_of_analysis: ""
    estimand: ""
    aggregation: ""
    independence: ""
    source_artifact: ""
    manuscript_blocks: []
```

## 主比較

- treatment:
- comparator:
- metric:
- direction / magnitude:

## Provenance

- artifact:
- script / workflow:
- input manifest:
- commit:

## Claim への接続

- 支える claim:
- claim role: core evidence / mechanism / boundary / robustness / negative control / exploratory
- scope:
- limitation:

## 次の route

- keep / split / merge / gate / analysis-request / defer
