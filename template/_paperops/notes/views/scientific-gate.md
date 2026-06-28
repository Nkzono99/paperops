---
view_type: pure_overview
starter_example_rows: true
source_of_truth:
  - _paperops/claims/gates/
  - _paperops/claims/claims/
  - _paperops/evidence/
authoritative_for:
  - overview
---

# 科学的ゲートビュー

このファイルは `_paperops/claims/gates/` の gate card を人間が俯瞰するためのビューである。gate 判定の正本は gate card に置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## Gate summary

- 現在の中心主張:
- 直近の gate verdict: 未記入
- Abstract / Conclusion に使ってよい claim:
- 書く前に止める claim:
- 中心仮定:
- claim upgrade blocker:
- 次の確認:

## Claim readiness table

| claim ID | gate card | claim | result / source / figure cards | estimand / metric | unit of analysis | comparison | evidence artifact | refs / related work | required checks | gate status | block reason | allowed wording | must-not-claim |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-0001 | GATE-0001 | 未記入 | RES-0001 / SRC-0001 / FIG-0001 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | independence / convergence / sensitivity / source-check | draft | 未記入 | 未記入 | 未記入 |

Gate status は `ready-to-write`、`analysis-needed`、`assumption-blocked`、`supplement-only`、`defer` のいずれかにする。

## Claim package checklist

| claim ID | 数値・単位確認 | 分母・条件名 | figure/table | manuscript block | provenance link | human approval | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-0001 | unchecked / checked | 未記入 | FIG-0001 | 未記入 | `_paperops/refs/links.toml` / `_paperops/notes/reproducibility.md` | not-needed / needed / approved | 未記入 |

## Required checks

- 時系列 snapshot を独立標本として扱っていないか:
- 最大値や favorable condition を主要証拠にしていないか:
- fraction / count / maximum は same denominator、same criterion、independence caveat を持つか:
- partial validation の validated scope と not covered を分けたか:
- path-dependent / threshold claim で endpoint metric、cumulative criterion、threshold barrier、initial-condition subset、decision threshold を分けたか:
- external validation needs を claim support ではなく claim upgrade blocker として扱ったか:
- claim stress-test の allowed wording と must-not-claim が Abstract / Conclusion / caption より先に固定されているか:
- proxy / sensitivity / authoring guard を measured model や validated solver output と誤読していないか:
- screening result と completed result を同じ推論に混ぜていないか:
- completed run / final snapshot を physical equilibrium、calibrated exposure、independent sample と誤読していないか:
- method novelty / representation claim に direct comparator が必要か。必要なら同じ総量・条件・estimator・denominator で比較されているか:
- convergence / sensitivity / target selection / mesh / integration range:
- figure の色域、decision boundary、threshold、軸、分母、二重軸、caption、本文参照:
- external crosswalk candidate の Main Figure label が、現行 manuscript figure set と figure role note に整合しているか:
- 反論・関連研究との接続:
- AI が転記した数値ではなく、解析 artifact から確認した数値か:

## Blocking issues

| issue ID | claim ID | type | 内容 | route | owner | status |
| --- | --- | --- | --- | --- | --- | --- |
| SG-0001 | CLM-0001 | analysis-needed / assumption-blocked / refs-needed / figure-needed | 未記入 | `/map-result-patterns` / `/research-related-work` / `_paperops/requests/analysis/` | human / AI | open |

## Approved writing scope

本文、Abstract、Conclusion、caption で言ってよい表現だけを書く。

- CLM-0001:

## Linked views

- `_paperops/notes/views/assumption-ledger.md`
- `_paperops/notes/views/claim-upgrade-gates.md`

## Human approval log

| date | decision | scope | approved by | notes |
| --- | --- | --- | --- | --- |
| 未記入 | 未記入 | 未記入 | 未記入 | 未記入 |

## Gate history

- 未記入
