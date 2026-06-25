# section contracts

`contracts/` は章ごとの文章テンプレートではなく、section と figure story の入出力契約を置く場所である。

各 contract は、その章が読者のどの疑問に答え、どの card / view / profile を入力にし、どの状態まで仕上げるかを定める。文言や段落数は固定しすぎない。

基本の流れ:

1. `plan-figure-story`: `figures.yml` と `manuscript/writing-profile.yml` を読み、claim の `visual_obligations` と figure card の `satisfies_visual_obligations` を対応させる。
2. `plan-section`: contract と `manuscript/writing-profile.yml` を読み、`paper_ir` の section plan を作る。
3. `draft-section`: section plan だけを主入力にして本文を書く。
4. `audit-section`: 公開原稿と contract を読み、契約違反を返す。

生成された section plan や figure candidate inventory は `.paperops/cache/` など Git 管理しない場所へ置く。正本は `evidence/`、`claims/`、`review/`、`requests/` の card と controlled authoring view に置く。
