---
id: FB-0001
type: feedback
source: human
source_mode: prompt
delegated_role: ""
subagent_report: ""
target:
  kind: manuscript_block
  id: ""
issue_type: overclaim
severity: major
upstream_routes:
  - claim_scope_change
route_explanation: ""
status: open
related_cards: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Feedback Card

## 指摘

人間のレビュー、プロンプト指示、査読コメントを要約する。raw confidential text は `_handoff/` に留め、tracked card には必要な要約と ID を残す。

subagent 由来の場合は `source_mode: subagent_report` とし、`delegated_role`、`subagent_report`、review round 側の integration decision を対応させる。orchestrator は subagent の文面をそのまま本文へ流し込まず、route_explanation と閉じる条件を補う。

## なぜ本文だけでは済まないか

原稿表現だけの問題か、claim / evidence / gate / figure / request へ戻す必要があるかを書く。

`upstream_routes` の label だけで終わらせず、route_explanation に前提、判断根拠、本文 claim への影響、閉じる条件を普通の文で書く。

## Upstream routes

- `claim_scope_change`: claim card の scope / limitation / status を変える。
- `storyline_change`: reader promise、evidence ladder、Results hierarchy、Discussion functions を見直す。
- `section_depth_blocker`: Results / Discussion の薄さが段落修正では済まず、section plan へ戻す。
- `results_hierarchy_gap`: Results が reader question / answer / quantity / figure / consequence の階層を持たない。
- `discussion_function_gap`: Discussion が mechanism_warrant、prior_work_delta、alternative_or_boundary、decisive_next_test を欠く。
- `scientific_gate_reopen`: gate card を analysis-needed / assumption-blocked へ戻す。
- `result_card_update`: result interpretation、estimand、denominator を直す。
- `figure_card_update`: figure story、caption、軸、色域、分母を直す。
- `source_card_update`: 関連研究、引用、反論文献を追加・修正する。
- `analysis_request`: 追加解析や再計算を `requests/analysis/` に切る。
- `writing_request`: 原稿 block の改稿を `requests/writing/` に切る。
- `submission_hygiene_only`: author metadata、license、venue formatting など投稿前 hygiene のみ。STRUCTURE_ACCEPTED 前は主作業にしない。
- `manuscript_only`: 上流カードを変えず本文だけ直す。

## 反映ログ

- card updates:
- manuscript edits:
- validation:
