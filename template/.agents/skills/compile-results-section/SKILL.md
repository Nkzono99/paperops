---
name: compile-results-section
description: Use when Results must be planned from claims, evidence, figures, and paper_ir before drafting or revising prose.
---

# compile-results-section

Results を実施順や保有情報順ではなく、読者の疑問順に変換する section compiler。`paper_ir` は生成一時物であり、手書き正本ではない。Writer には card 正本を直接渡しすぎず、必要な claims、evidence、requests、controlled authoring view だけを section plan に圧縮する。

## Inputs

- `_paperops/defaults/contracts/results.yml`
- `_paperops/contracts/results.yml` if project overlay exists
- `_paperops/defaults/contracts/figures.yml`
- `_paperops/contracts/figures.yml` if project overlay exists
- `_paperops/defaults/schemas/results-hierarchy.schema.json`
- `_paperops/model/editorial/results-hierarchy.yml`
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `manuscript/writing-profile.yml`
- necessary claim / evidence / request cards

新規 scaffold では project-owned の `_paperops/model/editorial/results-hierarchy.yml` を必須入力とする。既存下流 project は M0-0003 を採用するまで `storyline.md` の legacy Markdown Results hierarchy を fallback として利用できる。

本文生成前に `plan-figure-story` を通し、state/setup 図、criterion 図、primary evidence 図、mechanism/boundary 図が claim に対して足りているか確認する。既存図だけを監査して `figure_story_fixed` にしない。

## Compile Rule

`compile-results-section` は typed Results hierarchy の配列順と `next_item_id` chain を一致させ、各 `RHI-*` item を `reader question -> one-sentence answer -> quantitative evidence -> figure -> baseline / comparator rationale -> consequence` の subsection に変換する。caveat は主張の意味を変える場合だけ置く。

Results の subsection plan は、`reader_question`、`answer`、`evidence`、`baseline_or_comparator_rationale`、`scope`、`consequence` を必ず持つ。baseline、control、reference condition、comparator を使う場合は、それが何を隔離し、何を検証していないかを公開読者向けに書く。run inventory、解析を実施した順の列挙、同じ limitation の反復を topic sentence にしない。

Results hierarchy の値は `_paperops/model/editorial/results-hierarchy.yml` が正本であり、`_paperops/notes/views/storyline.md` には複製しない。storyline view の `Section depth map` と `Methods definition registry` へ接続する。図表を並べるだけ、代表値だけを置く、baseline の科学的役割や判定基準を Methods に接続しない、境界条件と感度解析を一段落へ圧縮する場合は section-depth blocker として扱う。

section plan を作る前に `python scripts/check-section-contracts.py --root . --strict` を実行し、`RHI-*` ID の一意性、各 `next_item_id` が配列上の次 item を指すこと、terminal item が空文字で終わることを確認する。typed file が存在する場合は strict checker が legacy Markdown より優先して読む。

AI Writer が「この claim を強めるために必要な追加作業」「後で埋める」などの authoring intent を Results prose に書きそうな場合は、本文にしない。近傍の `% INTENT:` / `% TODO-PAPER:` comment に残し、追加解析が必要なら `_paperops/model/issues/` へ切り出す。公開本文として意図的に扱う場合だけ `% paperops: allow-authoring-intent -- reason` を直前に置く。

必要な定量値、比較、panel が未実行だが、投稿前に現実的な追加シミュレーションとして閉じられる場合は、Future Work や defensive caveat へ回す前に `draft-predicted-results` を使う。Results prose に `xx` や予測図を置く場合は、近傍に `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:` を残し、対応する `_paperops/model/issues/analysis/` card があることを確認する。

## Section Depth

`manuscript/writing-profile.yml` の `section_depth` を確認する。`ja_chars` は日本語原稿の TeX noise を除いた文字数、`en_words` は英語原稿の TeX noise を除いた word count として扱う。`length_is_floor_not_target` の原則に従い、短い場合も水増ししない。

`section-depth-check` が Results を short と判定した場合は、subsection を増やすこと自体を目的にしない。reader question、answer、quantitative evidence、comparison、baseline/comparator rationale、scope、consequence のどれが欠けているかを特定し、one-paragraph subsections は統合するか、読者質問に答えるだけの内容を加える。

`section-contract-check` が Results hierarchy や Methods definition registry の不足を返した場合は、文章の水増しではなく `_paperops/notes/views/storyline.md` と Methods / Results plan を更新してから本文へ戻る。

Draft 後は `review-block-flow` で block operation table を作る。各 block の reader_question、author_move、why_here、next_block_expectation を確認し、必要なら keep / move / split / merge / delete / add を行ってから AUDITED 扱いにする。

生成した section plan は必要な場合だけ `.paperops/cache/section-plan-results.yml` に置き、Git 管理しない。本文を生成・修正した後は `make authoring-intent-check` を使い、AI 執筆意図が公開 prose に漏れていないことを確認する。

## P3 typed compile / Writer route

P2で四つのcompile authorityが採用済みなら、routineなcontext収集とscope検査を手作業で再実装せず、`pops compile prepare <SEC-ID>`、`pops write start <compile-id>`を使う。Writer workspaceは原稿全体を読み直せるので、candidate（候補）TeXを直接編集し、`pops write check <session-id>`で保存則、引用、数量、図、予測稿、JA/EN影響を確認する。局所修正ならcompile時に`--scope block --block <BLK-ID>`を明示する。

候補を読み返してResults hierarchyや全体の証明順が不適切なら、scopeを黙って広げない。`design-paper-storyline`でManuscript / Editorial Modelを改訂し、再承認・再compileする。`pops write apply <session-id> --yes`は人間が候補を確認した後だけ使う。living TeXの直接編集も引き続き有効であり、P3は意味論的判断を機械検査へ置換しない。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
