# project contract overlays

`_paperops/contracts/` は project-owned の contract overlay を置く場所である。

paperops-managed の既定 contract は `_paperops/defaults/contracts/` に置く。論文固有の変更が必要な場合だけ、同じファイル名の overlay をこのディレクトリに置く。読み取り側は `_paperops/contracts/` を優先し、なければ `_paperops/defaults/contracts/` を読む。

overlay は全文コピーよりも、差分が分かる小さな変更として扱う。汎用化できる改善は `/feedback-paper-harness` で upstream へ戻す。

基本の流れ:

1. `design-paper-storyline`: defaults または overlay の `storyline.yml` と `_paperops/notes/views/storyline.md` を読み、reader_promise、evidence_ladder、Results hierarchy、Discussion functions を固定する。
2. `plan-figure-story`: defaults または overlay の `figures.yml` と `manuscript/writing-profile.yml` を読み、claim の `visual_obligations` と figure card の `satisfies_visual_obligations` を対応させる。
3. `plan-section`: contract と `manuscript/writing-profile.yml` を読み、`paper_ir` の section plan を作る。
4. `draft-section`: section plan だけを主入力にして本文を書く。
5. `audit-section`: 公開原稿と contract を読み、契約違反を返す。

生成された section plan や figure candidate inventory は `.paperops/cache/` など Git 管理しない場所へ置く。正本は `_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` の card と controlled authoring view に置く。
