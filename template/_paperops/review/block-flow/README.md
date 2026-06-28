# block-flow review

`_paperops/review/block-flow/` は、Results / Discussion などの section を `AUDITED` または `ACCEPTED` に進める前に、block 単位の読み順、著者の判断、移動・分割・追加・削除の意思決定を残す場所である。

本文の良し悪しを採点する場所ではない。`review-block-flow` で、各 `% block:` に対して `reader_question`、`author_move`、`why_here`、`next_block_expectation`、`operation` を埋め、原稿編集や section plan 更新の根拠にする。

新規 review は `block-flow-review-template.md` をコピーして作る。`section` は `results` または `discussion` など対象 section 名にし、同じ section を `AUDITED` / `ACCEPTED` にする前に `make block-flow-review-check` を確認する。
