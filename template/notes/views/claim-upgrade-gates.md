# Claim Upgrade Gates View

このファイルは external validation needs、claim stress-test、observational boundary など、claim を強める前に止める gate を俯瞰するビューである。正本は `claims/gates/` の scientific gate card と、必要な `requests/analysis/` / `review/responses/` のカードに置く。

## Upgrade gate matrix

| gate ID | claim component | gate type | source artifact | blocking claim | allowed wording | must-not-claim | validated scope | not covered | route | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UPG-0001 | 未記入 | external-validation / claim-stress / observational-boundary / authoring-guard | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | 未記入 | research-request / limitation / response-matrix / defer | open |

## Guard

- external validation row は claim support ではなく claim upgrade blocker として扱う。
- claim stress-test は physical evidence ではなく allowed wording と must-not-claim を固定する authoring gate として扱う。
- `tracked=true`、`ready=1`、`non_consistent_rows=0` などの green metric があっても、allowed next action と forbidden next action を併記する。
- Abstract / Conclusion / Key Points / main caption へ進める前に、該当 claim component の upgrade gate が開いたままではないか確認する。
