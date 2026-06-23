---
id: FB-0001
type: feedback
source: human
source_mode: prompt
target:
  kind: manuscript_block
  id: ""
issue_type: overclaim
severity: major
upstream_routes:
  - claim_scope_change
status: open
related_cards: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Feedback Card

## 指摘

人間のレビュー、プロンプト指示、査読コメントを要約する。raw confidential text は `_handoff/` に留め、tracked card には必要な要約と ID を残す。

## なぜ本文だけでは済まないか

原稿表現だけの問題か、claim / evidence / gate / figure / request へ戻す必要があるかを書く。

## Upstream routes

- `claim_scope_change`: claim card の scope / limitation / status を変える。
- `scientific_gate_reopen`: gate card を analysis-needed / assumption-blocked へ戻す。
- `result_card_update`: result interpretation、estimand、denominator を直す。
- `figure_card_update`: figure story、caption、軸、色域、分母を直す。
- `source_card_update`: 関連研究、引用、反論文献を追加・修正する。
- `analysis_request`: 追加解析や再計算を `requests/analysis/` に切る。
- `writing_request`: 原稿 block の改稿を `requests/writing/` に切る。
- `manuscript_only`: 上流カードを変えず本文だけ直す。

## 反映ログ

- card updates:
- manuscript edits:
- validation:
