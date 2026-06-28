---
view_type: pure_overview
starter_example_rows: true
source_of_truth:
  - _paperops/requests/analysis/
  - _paperops/requests/writing/
authoritative_for:
  - overview
---

# 追加依頼ビュー

このファイルは `_paperops/requests/analysis/` と `_paperops/requests/writing/` のカードを人間が俯瞰するためのビューである。依頼の正本は request card に置く。

初期状態の `*-0001` 行は例示行であり、対応する実カードはまだ作成されていない。実カードを作成したら、この行を実 ID に置き換えるか削除し、`starter_example_rows` を `false` にする。

## Analysis requests

| request ID | card | requested by | related claim | target link | requested outputs | verification axis | runops_id | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AREQ-0001 | `_paperops/requests/analysis/AREQ-0001.md` | FB-0001 | CLM-0001 | _paperops/refs/links.toml | 未記入 | denominator / independence / convergence / external validation / figure redesign | blank / draft:* / queued ID | planned |

Analysis request status は `planned`、`predicted`、`running`、`executed`、`reconciled`、`abandoned` のいずれかにする。予測稿を本文 authoring source に置く場合は `predicted` または `planned` にし、submission candidate へ切る前に `executed` から `reconciled` へ進める。

## Writing requests

| request ID | card | requested by | target blocks | related claim | status |
| --- | --- | --- | --- | --- | --- |
| WREQ-0001 | `_paperops/requests/writing/WREQ-0001.md` | FB-0001 | 未記入 | CLM-0001 | draft |

## Handoff status

- runops へ渡した依頼:
- draft staged but not queued:
- 人間承認待ち:
- manuscript 反映待ち:
