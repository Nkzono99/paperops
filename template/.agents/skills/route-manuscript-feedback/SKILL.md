---
name: route-manuscript-feedback
description: Use when manuscript feedback, review comments, or revision requests need to be routed before editing prose.
---

# route-manuscript-feedback

Review 後や人間コメント後に、Reviewer にそのまま改稿させず、どの上流 loop に戻すかを決める skill。まず Issue Router として分類し、必要なら Backward propagation で card / request / section plan に反映してから本文を編集する。

## Workflow Phase

本文編集前に `pops workflow status` と `pops workflow next` を確認する。`_paperops/workflow/current-state.yml` に stale section がある場合、全文改稿へ進まず、該当 section の route を確認する。

`UNDER_REVIEW` 後は一方向に進めず、Issue Router で evidence / story / section / prose / submission loop のどこへ戻るかを決める。

claim、result、figure、section contract を更新した場合は `pops workflow invalidate <artifact-id>` を実行し、依存 section を `STALE` にする。guard を満たさない場合は、文章だけで `DRAFTED` や `STRUCTURE_ACCEPTED` に進めない。

## Issue Router

`_paperops/review/feedback/` の指摘を見て、まず次のどれかに分類する。

- `evidence_loop`: 数値、比較、収束、対照、artifact provenance が不足している。
- `story_loop`: 中心主張、figure story、結果階層、主図と補足図の切り分けが揺れている。
- `section_loop`: Methods の粒度、Results subsection、Discussion の推論型、section contract が合っていない。
- `prose_loop`: claim scope は変えず、名詞化、冗長、防御表現、段落流れだけを直す。
- `submission_loop`: 引用、開示、投稿先形式、bibliography、Data availability を直す。

`submission_loop` は content-first gate の後段である。Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が未解決なら、`submission_loop` ではなく `story_loop` または `section_loop` へ戻す。

分類したら `pops workflow route-review --issue-class <class>` で戻る深さを確認する。状態へ反映する場合だけ `--apply` を付ける。同じ issue class が既定回数を超えて再発した場合は、人間判断へ戻す。

## Backward propagation

feedback は必ず次のどれに属するかを判定する。

- `manuscript_only`: 誤字、局所表現、段落の流れ。
- `claim_scope_change`: 主張が強すぎる、弱すぎる、順序が悪い。
- `storyline_change`: reader_promise、evidence_ladder、Results hierarchy、Discussion functions が揺れている。
- `scientific_gate_reopen`: assumption、数値、比較、再現性、人間承認が未解決。
- `result_card_update`: 数値、分母、条件名、図表、artifact provenance。
- `source_card_update`: 引用、関連研究、反論文献、source verification。
- `analysis_request`: 追加解析、再計算、感度確認、図表差し替え。
- `response_only`: 原稿ではなく response letter で説明する。
- `section_depth_blocker`: Results hierarchy や Discussion functions が薄く、段落修正ではなく section plan へ戻す。
- `results_hierarchy_gap`: Results が図表・条件・実施順の列挙になっている。
- `discussion_function_gap`: Discussion が limitation 羅列で、mechanism_warrant、prior_work_delta、decisive_next_test がない。
- `submission_hygiene_only`: 投稿前 hygiene だけの問題。STRUCTURE_ACCEPTED 後にだけ扱う。

この判定をせずに本文だけを直すと、次の review loop で同じ問題が戻る。`_paperops/refs/` と `_paperops/notes/` に作る作業ドキュメントは日本語で書く。
