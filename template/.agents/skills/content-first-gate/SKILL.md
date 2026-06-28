---
name: content-first-gate
description: Use when manuscript work may drift from content repair into submission hygiene, harness maintenance, or low-impact polish.
---

# content-first-gate

原稿完成 lane の進路確認 skill。ここでの「投稿可能」は、まず story spine、Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が閉じていることを意味する。Submission hygiene は最後の hygiene であり、本文 blocker を解決しない。

## Priority

作業対象は次の順で決める。

1. **Manuscript content**: story spine、Results hierarchy、Discussion functions、claim scope、figure story、major review blocker。
2. **Evidence / claim repair**: quantity denominator、unit of analysis、assumption approval、analysis request、figure obligation。
3. **Prose polish**: claim scope を変えない段落流れ、terminology、mirror。
4. **Submission hygiene**: author metadata、license、Open Research DOI、venue formatting、cover letter、`make pre-submit`。

`STRUCTURE_ACCEPTED` が false、または `storyline_architecture_approved` / `results_hierarchy_defined` / `discussion_functions_defined` が false の間は、Submission hygiene を主作業にしない。`readiness-check --require-submission` の失敗は記録してよいが、原稿本文の blocker より優先しない。

下流 manuscript goal 中に readiness-check、Makefile、workflow、skill、template script の再利用可能な欠陥を見つけた場合、その場で下流ハーネスを改修しない。`feedback-paper-harness` 用に問題・再現・提案を要約し、原稿改善へ戻る。ユーザーが明示的に「下流ハーネスを直して」と依頼した場合だけ例外とする。

## Start self-critique

本文や metadata を触る前に、次を短く書く。

- `highest_priority_content_blocker`: 今もっとも大きい manuscript content blocker。
- `next_action_reduces_content_blocker`: 次の作業がその blocker をどう減らすか。
- `deferred_hygiene`: 今は扱わない Submission hygiene / downstream harness 作業。
- `route`: story_loop / section_loop / evidence_loop / prose_loop / submission_loop のどれか。

`_paperops/workflow/current-state.yml` の `CONTENT_FIRST.next_action_reduces_content_blocker` を満たせない場合、本文編集や Submission hygiene に入らず、`design-paper-storyline`、`integrate-writing-feedback`、または evidence / claim repair へ戻る。

## Course-correction checkpoint

次のいずれかが起きたら、作業を続ける前に進路修正を行う。

- `readiness-check` や `make pre-submit` が author metadata、license、venue formatting を指摘した。
- readiness-check、Makefile、script、workflow、skill など downstream harness を直したくなった。
- 30 分以上、Results hierarchy / Discussion functions / claim scope / figure story を進めずに周辺作業だけをしている。
- 新しい feedback が出て、route が manuscript_only か上位 loop か不明になった。

この checkpoint では `scripts/check-content-first.py --root . --phase progress --intent <content|evidence|prose|submission|harness> --strict` を使う。`CONTENT_FIRST` guard で最高優先 content blocker と next action の自己批判を記録し、content blocker が残る間に Submission hygiene や harness だけが changed file なら、その作業を止め、必要なら `feedback-paper-harness` へ要約して原稿へ戻る。

## Completion self-critique

完了宣言の直前に `make finish-manuscript-check` を実行する。`STRUCTURE_ACCEPTED` が未達、または reviewer loop の blocking / major concern が閉じていない場合、`make pre-submit` の一部が通っていても `/goal` を完了しない。

`check-content-first.py` は進路変更時の gate、`finish-manuscript-check` は goal 終了前の gate として使い分ける。
