---
name: review-block-flow
description: Use when a manuscript section has a draft, weak author stance, thin Results or Discussion, frozen block order, or needs block-level move/split/merge/delete/add review before AUDITED or ACCEPTED.
---

# review-block-flow

既存 block を温存したまま prose polish へ進まず、section architecture と author stance を block 単位で見直す。目的は、薄い構成を保存しないこと、そして読者がどの順で問い、判断し、納得するかを著者の意思として固定することである。

## When to Use

- `DRAFTED -> AUDITED` の前。
- Results / Discussion が短い、均等説明、弱い結論、limitation 羅列に見えるとき。
- 一度作った block の順序や粒度が、その後の evidence / figure / feedback に合っているか怪しいとき。
- prose は読めるが、reader question、author_move、why_here が弱いとき。

## Inputs

- 対象 section の TeX と `% block:` ID
- `_paperops/notes/views/storyline.md`
- `_paperops/defaults/contracts/<section>.yml` と project overlay
- 関連する claim / evidence / figure / source / feedback card
- 図を含む block では Figure design brief と `design-paper-figure` の reader_task

## Block Contract

各 block を次の観点で読む。

- `reader_question`: この block に入る時点の読者の問い。
- `author_move`: 著者がここで行う判断。problem framing / contrast / answer / mechanism / boundary / implication / transition など。
- `evidence_or_claim`: 支える result、claim、figure、source。
- `why_here`: なぜこの位置で読む必要があるか。
- `next_block_expectation`: 次の block に渡す問い、緊張、未解決点。

## 手順

1. 現在の block 順を列挙する。本文をまだ書き換えない。
2. section の約束を一文で書く。Results なら「何を示す順序か」、Discussion なら「何を解釈し、何を退け、何を保留するか」。
3. 各 block に `reader_question`、`author_move`、`why_here`、`next_block_expectation` を書く。
4. author stance を確認する。全 block が同じ温度で説明している場合は、assert / reject / boundary / hold を分ける。
5. block operation table を作る。operation は `keep`、`move`、`split`、`merge`、`delete`、`add` のいずれかにする。
6. `delete` は情報破棄ではない。本文主張に効かないなら supplement、note、source card、request へ移す。
7. `add` は水増しではない。reader question に答える証拠、比較、境界、含意が足りない場合だけ追加する。
8. 図で読ませる block は `design-paper-figure` の Figure design brief と caption intent を確認する。図の reader_task と block の author_move がずれるなら、図か block を戻す。
9. table を作った後にだけ、本文編集または section plan 更新へ進む。

## block operation table

```text
| block_id | reader_question | author_move | evidence_or_claim | why_here | next_block_expectation | problem | operation | target_order_or_new_block | rewrite_intent | upstream_updates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| results.core.01 | 未記入 | 未記入 | RES/CLM/FIG/SRC | 未記入 | 未記入 | weak order / duplicate / missing stance / unsupported | keep / move / split / merge / delete / add | 未記入 | 未記入 | none / claim / evidence / figure / source / request |
```

## Output

- `_paperops/review/block-flow/` の block operation table
- new block order
- author stance summary: assert / reject / boundary / hold
- section_loop or prose_loop recommendation
- upstream card / Figure design brief / request updates needed

`AUDITED` / `ACCEPTED` に進める前に `make block-flow-review-check` を実行し、Results / Discussion の `% block:` が table に揃っていることを確認する。

## Codex 実行メモ

- すべて `keep` にする場合も、各 block の `why_here` と `next_block_expectation` を書く。
- block を変えないことは選択であり、デフォルトではない。
- Results / Discussion が薄い場合、文量ではなく missing reader question、missing author_move、missing evidence、missing consequence のどれかへ戻す。
