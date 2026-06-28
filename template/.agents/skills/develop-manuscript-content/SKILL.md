---
name: develop-manuscript-content
description: Use when Codex needs to draft, expand, restructure, or revise manuscript content itself, including claims, storyline, figures, Results, Discussion, Methods, or prose, while keeping submission metadata and external sharing gates out of scope.
---

# develop-manuscript-content

原稿内容そのものを進める route-level skill。対象は claims、storyline、figure story、Results hierarchy、Discussion functions、Methods definition、section compiler、block flow、本文 prose である。`finish-manuscript` が投稿可能状態までの監督役なら、この skill は manuscript content だけを前に進める作業入口である。

投稿情報を埋める skill ではない。submission metadata、ORCID、affiliation、email、corresponding author、license、Data availability、Open Research DOI、投稿先フォーム、外部共有 artifact は主作業にしない。投稿候補化が目的になった時点で `submission-gate` に切り替える。

## Scope

| 扱う | 扱わない |
| --- | --- |
| central claim / claim scope | ORCID / affiliation / author metadata |
| storyline / reader promise / evidence ladder | license / DOI / repository URL の記入 |
| figure story / Figure design brief / caption intent | journal form / cover letter / submission portal |
| Results hierarchy / Discussion functions | submission candidate / round snapshot の freezing |
| Methods definition registry | `readiness-check --require-submission` の metadata 埋め |
| section draft / block operation / prose revision | PyPI、template release、harness 改修 |

## 最初に見る

- `story/story-seed.md`
- `_paperops/notes/project-brief.md`
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/scientific-gate.md`
- `_paperops/defaults/contracts/storyline.yml`
- `_paperops/defaults/contracts/results.yml`
- `_paperops/defaults/contracts/discussion.yml`
- `_paperops/defaults/contracts/methods.yml`
- `manuscript/writing-profile.yml`
- 対象 section と figure captions

存在しない file は blocker ではない。足りない場合は、本文へ直接補う前に必要な card、view、request、section plan のどこへ置くかを決める。

## Route

1. `content-first-gate` で、次の作業が manuscript content blocker を減らすか確認する。
2. claim scope や central claim が曖昧なら `scientific-gate` と `design-manuscript-claims` に戻す。
3. story spine、Results hierarchy、Discussion functions が弱いなら `design-paper-storyline` を使う。
4. 図が evidence path を支えるなら `plan-figure-story` で visual obligation を作り、個別図は `design-paper-figure` で reader task と acceptance criteria を固定する。
5. 追加シミュレーションで投稿前に閉じられる Results / Discussion blocker は、Future Work に逃がさず `draft-predicted-results` で予測稿と analysis request にする。
6. 必要な card と controlled authoring view から `paper_ir` を作り、`compile-results-section`、`compile-discussion-section`、`compile-methods-section` で読者向け構造へ変換する。
7. draft section は `review-block-flow` で block operation table を作り、keep / move / split / merge / delete / add を判断してから AUDITED へ進める。
8. AI Writer の authoring intent、後で埋める内容、作業計画は本文 prose にせず、`% INTENT:` / `% TODO-PAPER:`、notes、requests に分ける。
9. 人間レビューや自然文指示が来たら `integrate-writing-feedback` と `route-manuscript-feedback` で evidence / story / section / prose の戻り先を決める。

## Stop Rules

- submission metadata だけが未記入なら、この skill で埋めない。原稿内容が accepted なら `finish-manuscript` または `submission-gate` へ渡す。
- ORCID、affiliation、license、Open Research DOI、readiness-check 改修を、Results hierarchy / Discussion functions / figure story の代わりに処理しない。
- 作業が template script、Makefile、release、harness 改修へ逸れそうなら、原稿改善を止めずに `feedback-paper-harness` へ要約する。
- 迷ったら「次の変更は読者の理解、主張の妥当性、図の意味、section の機能のどれを改善するか」を一文で書けるか確認する。

## 出力

- `Content status`: claim / storyline / figure / Results / Discussion / Methods / prose の未解決 blocker
- `Next manuscript edits`: 更新する section block、card、view、request
- `Figure or analysis requests`: 作る図、追加シミュレーション、予測稿の扱い
- `Block-flow decisions`: keep / move / split / merge / delete / add
- `Deferred submission items`: この skill では扱わず `submission-gate` へ渡す metadata 項目

