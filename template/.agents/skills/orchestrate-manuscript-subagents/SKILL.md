---
name: orchestrate-manuscript-subagents
description: Use when manuscript finishing will delegate review, evidence, story, figure, or submission checks to subagents.
---

# orchestrate-manuscript-subagents

subagent を使える環境で、main agent が writer ではなく **orchestrator** として動くための skill。subagent reports are not manuscript edits: 出力は `subagent_report`、feedback card 案、route recommendation、claim/evidence/section plan 更新案であり、同じ manuscript block を複数 agent に直接編集させない。

## Inputs

`_paperops/defaults/workflow/subagent-roster.yml` と、存在する場合だけ `_paperops/workflow/subagent-roster.yml` overlay を読む。今の blocker に効く role だけを選び、brief には role、target artifact、allowed inputs、forbidden inputs、expected output path、route question、completion signal を入れる。

raw confidential reviewer text、未公開データ、個人情報、ローカル絶対パスは、許可と範囲が明示されるまで渡さない。公開原稿だけの模擬査読なら、repo 内部ノートを渡さず public artifact だけを渡す。

## Standard Roles

- `story_architect`: story spine、reader promise、Results hierarchy、Discussion functions を俯瞰し、story_loop / section_loop を判定する。
- `evidence_auditor`: claim、quantity、denominator、assumption、analysis request の不足を evidence_loop へ戻す。
- `results_structure_reviewer`: Results が reader question -> answer -> quantitative evidence -> figure -> consequence になっているかを見る。
- `discussion_function_reviewer`: Discussion が mechanism warrant、prior-work delta、alternative/boundary、implication、decisive next test を持つかを見る。
- `figure_story_reviewer`: visual obligation、main / supplement split、caption と本文参照の欠落を見る。
- `public_reader`: 公開原稿だけを読み、未定義語、読者遷移、再現性ギャップを出す。
- `reviewer_panel`: major / minor / meta-review を分け、blocking concern を feedback loop に戻す。
- `submission_hygienist`: STRUCTURE_ACCEPTED 後にだけ author metadata、license、venue formatting、cover letter、`make pre-submit` を扱う。

## Integration

main agent は各 `subagent_report` を読んで重複をまとめ、`_paperops/review/rounds/` の Subagent delegation ledger に delegated_role、target、route recommendation、integration decision を記録する。

受理した指摘は `_paperops/review/feedback/`、`_paperops/claims/`、`_paperops/evidence/`、`_paperops/requests/`、`_paperops/notes/views/storyline.md`、section plan のどれかへ先に反映し、その後に本文を編集する。

`integration decision` は `accepted_to_feedback_card`、`accepted_to_claim_or_evidence_update`、`accepted_to_section_plan`、`deferred_with_reason`、`rejected_with_reason`、`requires_human_decision` のいずれかを使う。判断不能なものは本文へ混ぜず、人間判断か feedback card へ戻す。
