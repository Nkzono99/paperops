# PaperOps 2 評価 fixture 方針

この文書は、PaperOps 2 の新旧 pipeline を同じ入力で比較する評価 fixture の保存場所と必須項目を定める。schema 適合 fixture 本体は P1 で追加する。この方針追加だけで P1 以降の機能を提供済みとは扱わない。

## 予約パス

P1 で `tests/fixtures/editorial/` 配下に次のカテゴリを作成する。

- `tests/fixtures/editorial/mechanism-led/`: 主要結果から機構説明を選ぶ case
- `tests/fixtures/editorial/boundary-led/`: 成立範囲や境界条件が中心になる case
- `tests/fixtures/editorial/negative-result-led/`: 当初仮説を支持しない結果から論旨を再構成する case

各カテゴリは少なくとも1つの case を持ち、個別 case をカテゴリ配下のディレクトリとして保存する。

## Case の必須項目

各 case は実案件の複製ではなく、再配布できる合成データとする。次をすべて保持する。

- 最低2つの `story candidates`
- 採用候補ごとの `selection reason`
- 不採用候補ごとの `rejection reason`
- 期待する `Results hierarchy`
- 各 claim の `claim role`
- 各論証段階の `argument move`
- 新旧 pipeline の比較で期待する diagnostic

story 選択と却下の根拠は同じ case 内で追跡できるようにし、Results hierarchy、claim role、argument move、期待 diagnostic の対応を失わないこと。

## Private 案件

private 案件の入力、出力、中間 state は repo 外で評価する。private 案件と raw data は repo に追跡しない。この repo には、案件、人物、研究内容を再識別できない sanitized aggregate だけを残す。private 案件から合成 fixture を作る場合も、値の置換だけではなく、固有の論理構造や文言を引き継がない。
