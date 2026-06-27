---
name: finish-manuscript
description: Use when /goal asks Codex to finish a manuscript from scratch, revise an existing draft, or supervise a manuscript feedback loop through completion.
---

# finish-manuscript

原稿を投稿可能な状態まで進める route-level skill。1から書く場合、既存稿を仕上げる場合、査読や人間コメントから response を作る場合の入口だが、詳細手順は専門 skill に委譲する。

この skill は **content-first** の監督役であり、本文 blocker を減らす順路を決める。Submission hygiene は原稿本文の story spine、Results hierarchy、Discussion functions、claim scope、figure story、major review blocker が閉じた後の最終面である。

main agent は writer だけでなく orchestrator として動く。subagent を使う場合は `orchestrate-manuscript-subagents` を先に読み、report を本文へ直接混ぜず、claim / evidence / feedback / section plan へ統合する。

## 最初に決める

- `from-scratch`: 実質的な原稿がまだ無い。`scientific-gate`、`design-manuscript-claims`、`design-paper-storyline` を通してから本文へ進む。
- `revision`: 既存稿、AI 初稿、人間レビュー、PDF 指摘、editor decision のいずれかがある。`integrate-writing-feedback` と `route-manuscript-feedback` で戻る深さを決める。
- `response`: 実査読への改訂が主目的。`respond-to-peer-review` を主ルートにし、この skill は Finish criteria と feedback loop を監督する。

最初に読むものは最小にする。`_paperops/notes/project-brief.md`、`manuscript/venue.md`、`_paperops/notes/views/storyline.md`、`_paperops/workflow/current-state.yml`、`manuscript/writing-profile.yml`、`_paperops/review/feedback/`、`_paperops/review/rounds/`、`_paperops/requests/` を確認し、必要な詳細は専門 skill に任せる。

対象原稿が repo 外なら `import-manuscript` で取り込む。raw confidential reviewer text や雑多な人間入力は `_handoff/` に置き、tracked card には要約、ID、route だけを残す。

## Route

1. `content-first-gate` で Start self-critique を行い、次の作業が manuscript content blocker を減らすか確認する。
2. story spine が弱い場合は `design-paper-storyline` を editorial architect として使い、Results hierarchy と Discussion functions を確認する。
3. 図表が本文生成後の飾りになりそうなら `plan-figure-story` で visual obligation と main / supplement split を先に決め、必要なら `figure-obligation-check` で欠落を確認する。
4. Writer に生の card ontology を直接渡さない。必要な card と controlled authoring view から `paper_ir` を作り、`compile-results-section`、`compile-discussion-section`、`compile-methods-section` で読者向け構造へ変換する。
5. AI Writer の authoring intent、判断保留、後で埋める内容、作業計画は本文 prose に書かない。近傍の `% INTENT:` または `% TODO-PAPER:` に残し、未解決なら `_paperops/notes/` / `_paperops/requests/` へ移す。
6. review 後や route が不明な feedback は `route-manuscript-feedback` に渡し、evidence / story / section / prose / submission loop のどこへ戻すか決める。
7. 模擬査読や公開原稿確認が必要なら `review-public-manuscript` と `peer-review-manuscript` を回し、blocking / major concern を `integrate-writing-feedback` へ戻す。
8. 完了前に `finalize-manuscript` を読み、Finish criteria、human approval、`make finish-manuscript-check`、必要な audit / ci を確認する。

## Lane Notes

From-scratch lane では、文章生成へ急がず、core claim、essential results、storyline、figure story、paper_ir を先に揃える。`design-manuscript-claims` で keep / compress / move / cut を決め、承認が必要な assumption や claim scope は human approval なしに中心主張へ昇格しない。

Revision lane では、現稿の読みと feedback を分ける。AI 初稿や Results / Discussion の薄さが目立つ場合は `audit-ai-draft` と `design-paper-storyline` へ戻り、本文編集は上流 card と section plan の更新後に行う。

Response lane では、`respond-to-peer-review` の comment inventory、response matrix、revision plan、response letter と本文変更を対応させる。査読対応だけで本文の claim scope を変える場合は `route-manuscript-feedback` へ戻す。

## Stop Rules

- `content-first-gate` が content blocker 未解決と判定する間は、Submission hygiene や downstream harness 改修を主作業にしない。
- `paper_ir` や section plan は生成一時物であり、必要な場合だけ `.paperops/cache/` に置く。
- AI の執筆メモを読者向け本文に混ぜない。`% INTENT:` / `% TODO-PAPER:` は回収可能な TeX comment として使い、公開本文に意図的に残す場合だけ `% paperops: allow-authoring-intent -- reason` を置く。
- `/goal` 中は今の blocker、次の 1-3 手、Finish criteria の未達項目を短く更新する。
- 迷ったら prose polish ではなく、evidence、story、section、feedback route のどこが詰まっているかを先に決める。
