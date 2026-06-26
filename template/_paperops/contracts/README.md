# section contracts

`_paperops/contracts/` は章ごとの文章テンプレートではなく、storyline、section、figure story の入出力契約を置く場所である。

各 contract は、論文全体または各章が読者のどの疑問に答え、どの card / view / profile を入力にし、どの状態まで仕上げるかを定める。文言や段落数は固定しすぎない。

基本の流れ:

1. `design-paper-storyline`: `storyline.yml` と `_paperops/notes/views/storyline.md` を読み、reader_promise、evidence_ladder、Results hierarchy、Discussion functions を固定する。
2. `plan-figure-story`: `figures.yml` と `manuscript/writing-profile.yml` を読み、claim の `visual_obligations` と figure card の `satisfies_visual_obligations` を対応させる。
3. `plan-section`: contract と `manuscript/writing-profile.yml` を読み、`paper_ir` の section plan を作る。
4. `draft-section`: section plan だけを主入力にして本文を書く。
5. `audit-section`: 公開原稿と contract を読み、契約違反を返す。

生成された section plan や figure candidate inventory は `.paperops/cache/` など Git 管理しない場所へ置く。正本は `_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` の card と controlled authoring view に置く。
