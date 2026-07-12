# _paperops/notes/views

`_paperops/notes/views/` はカード層を人間が俯瞰し、本文へ変換するときの判断を置くための view 層である。

正本は `_paperops/model/research/`、`_paperops/model/research/`、`_paperops/model/issues/`、`_paperops/model/issues/` のカードである。カードの status、依存関係、route と矛盾する場合はカード側を優先する。

## View types

`_paperops/notes/views/` には二種類の view がある。

各 view は YAML front matter に `view_type` と `source_of_truth` を持つ。迷った場合はまず front matter を見る。

- `view_type: pure_overview`: 正本カードを読むための総覧。判断の正本は `source_of_truth` に戻す。
- `view_type: controlled_authoring`: カード正本の意味を本文語彙、条件名、読者順序へ変換するための編集可能な統制ビュー。科学的主張や証拠そのものの正本ではない。

starter template の `CLM-0001`、`RES-0001`、`FIG-0001` などの `*-0001` 行は、schema と記入粒度を示す例示行であり、実カード在庫ではない。実カードを作成したら該当行を実 ID に置き換えるか削除し、front matter の `starter_example_rows` を `false` にする。

### pure overview view

pure overview view は、カード正本を人間が読むための集約である。必要なら手で更新してよいが、判断の正本は対応する card に戻す。

- `claim-evidence-map.md`: claim / evidence / gate の総覧 cache。claim の正本は `_paperops/model/research/claims/`、gate の正本は `_paperops/model/research/gates/`、証拠の正本は `_paperops/model/research/` に置く。
- `result-pattern-map.md`: result / figure card の見取り図。result の正本は `_paperops/model/research/results/` と `_paperops/model/research/figures/` に置く。
- `scientific-gate.md`: gate card を人間が読むための総覧。判定の正本は `_paperops/model/research/gates/` に置く。
- `peer-review.md`: feedback / review round / response card の総覧。個別指摘の正本は `_paperops/model/issues/feedback/` に置く。
- `research-requests.md`: analysis / writing request card の総覧。依頼の正本は `_paperops/model/issues/` に置く。
- `assumption-ledger.md`, `claim-upgrade-gates.md`: gate card の assumption や upgrade blocker を読むための view。

### controlled authoring view

controlled authoring view は、カード正本の意味を本文語彙や読者向け条件へ変換するための編集可能な統制ビューである。これは単なる派生 cache ではないが、科学的主張や証拠そのものの正本ではない。

- `concept-terms.md`: claim / argument / evidence card の意味を本文語彙へ写すときの view。concept-term compression、つまり強い英語名詞句への単語化を見つけたら、強調語として accepted にするか、普通の文へほどくか、avoid にして本文から外す。
- `condition-context-map.md`: local condition、denominator、case count、run inventory を読者向けの公開条件名へ変換する view。
- `argument-map.md`: section role、reader job、本文順序、defense budget を本文構成へ写す view。argument card の正本は `_paperops/model/editorial/editorial-model.yml` に置く。

## paper_ir への接続

`paper_ir` は、カード正本と controlled authoring view から Writer に渡す context を作る生成一時物である。新しい手書き正本にはしない。

本文生成前に `plan-figure-story` で claim の visual obligation と主図/補足図の切り分けを決める。section compiler はその後に `paper_ir` を使って、Methods / Results / Discussion の reader question、answer、evidence、figure、caveat location、sentence budget、forbidden_terms を決める。Writer には生の card ontology を直接渡しすぎない。
