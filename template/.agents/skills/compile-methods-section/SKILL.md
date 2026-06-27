---
name: compile-methods-section
description: Use when Methods must be planned from method units, reproducibility needs, and paper_ir before drafting or revision.
---

# compile-methods-section

Methods を bookkeeping と物理モデル説明に分け、読者が再実装できる粒度へ変換する section compiler。`paper_ir` は生成一時物であり、手書き正本ではない。

## Inputs

- `_paperops/defaults/contracts/methods.yml`
- `_paperops/contracts/methods.yml` if project overlay exists
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- method-related evidence cards
- code / manifest pointers
- `manuscript/writing-profile.yml`

`manuscript/writing-profile.yml` の paper type overlay、投稿先、分野別要求を section contract に重ねる。境界条件、状態量、推定量、収束や検証が Results の解釈を変える場合は本文側に残す。

## Compile Rule

`compile-methods-section` は、method unit ごとに本文 / supplement / code の配分を決める。非標準か、結果がその選択に敏感か、読者が再実装するために必要か、引用で代替できるかを見る。

Results や figure caption に出る推定量、baseline/control、comparison、decision criterion、threshold、verification は、Methods definition registry に登録してから本文へ出す。登録単位は `estimand_and_unit_of_analysis`、`comparison_or_baseline`、`decision_criteria`、`verification_or_convergence` を最低限とし、`_paperops/notes/views/storyline.md` の `Methods definition registry` へ definition location と manuscript block を残す。

AI Writer が Methods prose に「後で埋める」「TODO」「authoring note」のような未解決作業を混ぜる場合は本文にしない。近傍の `% INTENT:` / `% TODO-PAPER:` comment、または `_paperops/requests/` へ残す。

配置判断は次の語彙を使う。

- `main_text`: 結果の解釈を変える情報、モデルの仮定、境界条件、推定量、検証の要点。
- `supplement`: 独立再現に必要だが読み筋を止める詳細、追加表、派生式。
- `code_or_manifest`: 実行ログ、file format、乱数台帳、環境情報、機械的な provenance。

method unit の plan には、`role_in_claim`、`nonstandard_choice`、`sensitivity_to_results`、`reimplementation_need`、`placement`、`citation_or_code_pointer` を持たせる。引用で代替できる既知手順を本文で長く説明しない一方、結果感度がある選択を supplement だけに逃がさない。

`section-contract-check` が Methods definition registry の不足を返した場合は、Results の prose を先に直さない。Methods plan に criterion glossary と baseline/comparator の scientific role を追加し、必要な `% block:` ID を作ってから Results / captions へ戻る。

生成した section plan は必要な場合だけ `.paperops/cache/section-plan-methods.yml` に置き、Git 管理しない。本文を生成・修正した後は `make authoring-intent-check` を使い、AI 執筆意図が公開 prose に漏れていないことを確認する。
