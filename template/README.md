# paper-my-topic

## P7 new-project default

通常の`pops init`で作成したprojectは、Research / Editorial / Results hierarchy / Manuscript / Issue / Publicationとtyped workflowを`v2-authoritative`で開始する。六モデルのstarter hashは`.pops/manifest.toml`に記録される。既存projectの`setup` / managed updateはauthorityを変えず、legacy artifact、互換reader、living TeXを削除しない。

## P4 typed workflow（opt-in）

P4では`pops workflow status --json`が六モデルから`INGESTED / MODELED / ARCHITECTED / DRAFTED / PUBLISHABLE`を投影する。査読論点は独立した`ISS-*`として`pops workflow issue route|close|reopen`でplan化し、owner-local approvalは`pops workflow approval decide`で対象revision/hashへ固定する。tracked反映は`pops workflow apply <plan-id> --yes`だけが行う。既存projectは`pops workflow migrate diff`でshadowを確認してから採用し、legacy workflowを削除しない。

## P3 typed compile / Writer（opt-in）

P2で四つのcompile authorityを採用した後は、`pops compile prepare <section|all>`で全体文脈と固定scopeを生成し、`pops write start <compile-id>`で原稿全体を読めるcandidateを作る。candidate TeXは直接編集し、`pops write check` / `diff`、人間確認後の`apply --yes`、必要時の`rollback`を使う。read contextとwrite scopeは別であり、局所scopeでは直せない場合はEditorial / Manuscript Modelを改訂して再compileする。P3はliving TeX直接編集やlegacy writerを削除しない。

`pops init` で作成される個別論文プロジェクトのスターター。

この scaffold では、人間が普段見る面と AI が執筆に使う内部状態を分ける。人間側は prompt、`story/`、`manuscript/`、`submission/`、レビューコメントを主な接点にする。AI/ハーネス側の evidence、claims、refs、requests、workflow、contracts、notes/views は `_paperops/` に置く。

## 初回セットアップ

まず `/setup` を使う。`pops init` で作った新規 repo はすでに `.pops/manifest.toml` を持つため、手で進める場合の最小手順は次の通り。

1. リポジトリ名とこの README を実プロジェクト名に合わせる。
2. `uvx --from paper-harness-cli pops doctor` で `.pops/manifest.toml` と構造を確認する。
3. `_paperops/refs/links.toml` を調整し、個人環境の実パスは ignored な `_paperops/refs/local/locations.toml` に書く。
4. 人間から AI へ渡す未整理ファイルは `_handoff/` に置く。
5. `story/story-seed.md`、`manuscript/venue.md`、`manuscript/publication-metadata.toml` を埋める。
6. 必要なら `tex-env.example.toml` を `tex-env.toml` にコピーして TeX 環境を設定する。

既存 repo を paperops 管理に採用するときだけ `uvx --from paper-harness-cli pops setup [path]` を使う。

`pops` は `uvx --from paper-harness-cli pops ...` で実行する。プロジェクト用 Python 環境が必要な場合だけ `make venv` を使う。

## 日常の流れ

1. `/resume-session` で前回の状態を読む。
2. `story/story-seed.md` で、研究質問、初期メカニズム仮説、期待する evidence path、結果が外れた場合の分岐を確認する。
3. `pops workflow status` と `pops workflow next` で、全体状態と stale section を確認する。
4. 原稿内容を進めるときは `/develop-manuscript-content` を入口にし、claims、storyline、figure story、section compiler、block-flow review、本文 prose を扱う。新規 scaffold の Results hierarchy は `_paperops/model/editorial/results-hierarchy.yml` を正本にする。`/finish-manuscript` は投稿可能状態までの監督入口として使う。
5. 図表が本文の主張を支える場合は `/plan-figure-story` を入口にし、必要な個別図だけ `design-paper-figure` や `figure-story-audit` へ進める。
6. 未実行だが投稿前に現実的に実施できる追加シミュレーションがあり、期待結果の根拠を書ける場合は `/develop-manuscript-content` 内の予測稿 route で扱う。本文には `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:` と `xx` 置換条件を残し、`_paperops/requests/analysis/` と接続する。
7. DRAFTED section は block flow を見直してから AUDITED 扱いにする。直接 `review-block-flow` を呼ぶのは、block 構成の再設計が明示された場合に限る。
8. subagent を使う場合、main agent は orchestrator として role brief と integration decision を `_paperops/review/rounds/` に残す。通常は `/finish-manuscript` から必要時に委譲する。
9. `manuscript/ja/` を中心に書く。AI Writer の執筆意図、判断保留、後で埋める内容は本文 prose ではなく `% INTENT:` または `% TODO-PAPER:` コメントに置き、必要なら `_paperops/notes/` / `_paperops/requests/` へ移す。
10. 必要な block を `manuscript/en/` に同期する。
11. 人間レビューや自然文の指示は `/integrate-writing-feedback` で feedback card にし、`route-manuscript-feedback` と `pops workflow route-review` で戻る深さを決める。
12. Submission hygiene と投稿メタデータは STRUCTURE_ACCEPTED 後に主作業にする。`manuscript/` は living authoring source で、投稿後や査読後も revision-authoring に戻して編集できる。投稿用の submission candidate / round snapshot は `submission/` と `_paperops/workflow/submission-ledger.yml` に記録し、完了前は `finalize-manuscript` と `make finish-manuscript-check`、共有前は `make ci` と `make audit`、投稿前は `submission-gate`、`make submission-gate`、ORCID や affiliation を含む `manuscript/publication-metadata.toml` の `[submission]`、`[open_research]`、`[human_verification]` を埋めた `make pre-submit` を実行する。

## 中間層

- `story/`: 人間が読む高次ストーリーと story seed
- `_paperops/evidence/`: result / figure / source card の正本
- `_paperops/claims/`: claim / scientific gate / argument card の正本
- `_paperops/review/`: feedback / review round / response card の正本
- `_paperops/review/block-flow/`: AUDITED / ACCEPTED 前の block operation table と author stance
- `_paperops/requests/`: analysis / writing request card の正本
- `_paperops/notes/views/`: `view_type` / `source_of_truth` つきの pure overview view と controlled authoring view
- `_paperops/model/editorial/results-hierarchy.yml`: project-owned の typed Results hierarchy 正本。各 item は `RHI-*` ID と `next_item_id` で読者順を表す。
- `_paperops/model/editorial/editorial-model.yml`: project-owned の story candidate、選択・棄却理由、argument move の正本。
- `_paperops/defaults/schemas/registry.yml` と JSON Schema: paperops-managed の registry / schema default。project-owned model state は置かない。
- `_paperops/defaults/contracts/`: paperops-managed の標準 section / figure story 契約
- `_paperops/contracts/`: project 固有の contract overlay
- `_paperops/workflow/`: 現在状態、section 状態、issue class、stale 伝播、人間判断
- `_paperops/defaults/workflow/subagent-roster.yml`: subagent role、delegation contract、orchestrator の integration decision 契約
- `manuscript/writing-profile.yml`: 論文種別・投稿先ごとの overlay と `section_depth` floor。JA は `ja_chars`、EN は `en_words` として数え、長さは target ではなく floor として扱う。

`paper_ir` は card と controlled authoring view から Writer に渡す context を作る生成一時物であり、手書き正本にはしない。

既存下流 project は M0-0003 を採用するまで `storyline.md` の legacy Markdown Results hierarchy を fallback として利用できる。移行時は `uvx --from paper-harness-cli pops update-paperops --apply --only _paperops/defaults/schemas/` で managed schema を更新し、project-owned の typed file を opt-in で作成する。`python scripts/check-section-contracts.py --root . --strict` が成功する前に legacy Markdown を削除しない。

新規 project は `pops init` で Research、Editorial、Results hierarchy、Manuscript、Issue、Publication の六モデル starter を受け取る。Research / Manuscript / Issue は架空 record のない空 index、Publication は未提出のaggregate starterである。既存projectはmanaged registry / schema / checkerを更新した後、`pops model status|validate|diff|adopt|rollback`でmodel単位に移行する。定型的なinventory、hash、snapshot、recoveryはdeterministic CLIが扱い、AIはscientific / editorial judgmentや人間承認を代替しない。

既存projectでは、最初に`pops model diff <model>`でshadowだけを作り、reportと`pops model validate <model> --strict`を確認する。authority切替は`pops model adopt <model> --yes`、復元は`pops model rollback <model>`を使う。P2後もlegacy card / review / requestを削除せず、human-edited TeXを維持する。既存workflow authorityも`pops workflow migrate diff`から別途opt-inし、採用まではlegacyをrollback可能なまま保持する。

`make schema-check` は schema / references / semantics / hash phaseをadvisoryに検査する。`editorial-model.yml`を含むproject-owned stateのauthority切替前は明示strict検査と人間承認を要求し、legacy controlled viewを維持する。

## 情報の置き場所

- `_handoff/`: 人間から AI へ渡す未整理ファイル。内容は Git 管理しない。
- `_archives/`: 1から書き直すための sealed scratch archive。通常の AI 執筆では読まない。
- `_paperops/refs/summaries/`: 採用する文献や外部 source の確認済み要約。
- `_paperops/refs/research/`: 関連研究調査の設計と raw finding。
- `_paperops/refs/source-reach/`: Web、GitHub、動画、RSS、SNS など外部 source channel の調査メモ。
- `_paperops/evidence/sources/`: summary だけでは足りない claim_boundary、parameter_choice、reviewer_objection、method_precedent の source card。
- `_paperops/refs/links.toml`: 共有できる外部 project / directory link の意味。
- `_paperops/refs/imports/`: 外部 export bundle の source index、integrity、claim role、取り込み状態。
- `_paperops/refs/local/locations.toml`: 個人環境の実パス。Git 管理しない。

過去稿を封印して同じ repo で書き直す場合は、`pops scratch restart --yes` を使う。archive だけを作る場合は `pops scratch archive`、既存 archive の確認や復元には `pops scratch list`、`pops scratch inspect`、`pops scratch restore` を使う。archive は `_archives/` に split bundle として置かれ、通常の skill は参照しない。

`_paperops/` に作る作業用ドキュメントは日本語で書く。citation key、TOML field name、外部ツール名などの識別子は英語のままでよい。

## 主要スキル

- `/source-reach-scan`, `/research-related-work`: 外部 source と関連研究を整理する。
- `/map-result-patterns`, `/scientific-gate`: 結果を証拠カードにし、主張として書けるか判定する。
- `/plan-figure-story`: 本文生成前に claim から visual obligation、Figure 1、主図/補足図、missing figure を設計する。
- `/develop-manuscript-content`: 原稿内容専用の route-level 入口。claims、storyline、figure story、Results hierarchy、Discussion functions、Methods definition、section compiler、`draft-predicted-results`、`review-block-flow`、本文 prose を扱い、ORCID、affiliation、license などの投稿メタデータは扱わない。
- `/finish-manuscript`: `/goal` で原稿完成まで進める薄い route-level 入口。原稿内容は `/develop-manuscript-content`、投稿候補化は `/submission-gate` へ委譲し、`draft-predicted-results` を含む content route と final checks を監督する。
- `/submission-gate`: `manuscript/` の authoring source から submission candidate / round snapshot を切り出す前に、予測稿、open AREQ、`xx`、AI intent、submission drift を strict に確認する。
- `/design-paper-storyline`: 原稿全体の story spine、typed Results hierarchy、Discussion functions を俯瞰し、Submission hygiene へ逸れる前に本文 blocker を固定する。
- `/review-public-manuscript`, `/peer-review-manuscript`: 公開原稿や投稿前原稿を読者・査読者目線で読む。
- `/respond-to-peer-review`: 実査読コメントへの返答を整理する。
- `/integrate-writing-feedback`: 人間レビューや指示を上流カードと原稿へ反映する。
- `/archive-scratch`: 過去稿を封印し、1から書き直すための reset / restore を安全に扱う。
- `/open-paper-scan`: まだ記録や実装に固定せず、俯瞰的な違和感や改善案を出す。
- `/feedback-paper-harness`: 再利用可能な摩擦を上流 `paperops` に戻す。

## ディレクトリ

- `story/`: 人間向けの構想、story seed、上位ストーリーライン
- `manuscript/`: 日英原稿、共有アセット、ミラー制御、投稿先情報
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX
- `_paperops/`: AI/ハーネス内部 state
- `_paperops/defaults/`: paperops-managed の標準 contract、schema、workflow kernel
- `_paperops/model/editorial/`: project-owned の typed editorial state
- `_paperops/contracts/`: Introduction / Methods / Results / Discussion / Conclusion と figure story の project overlay
- `_paperops/workflow/`: 現在状態、review round summary、人間判断、任意の workflow overlay
- `_paperops/refs/`: 文献、外部 source、外部 link、ローカルパス alias
- `_paperops/evidence/`, `_paperops/claims/`, `_paperops/review/`, `_paperops/requests/`: 論文を書く前後のカード層
- `_paperops/notes/`: AI 利用、再現性、handoff、decision log、controlled authoring view
- `_handoff/`: 未整理入力の一時受け取り箱
- `_archives/`: sealed scratch archive
- `.agents/`, `.claude/`: Agent / Claude Code 用 skill
- `scripts/`: 検証、ビルド、レビュー回収、ミラー確認
- `TROUBLESHOOTING.md`: nested repo や Windows safe.directory などの注意

paperops-managed core を project 固有に fork する必要がある場合は、まず `AGENTS.project.md`、`CLAUDE.project.md`、`Makefile.project`、project skill、または `_paperops/contracts/` / `_paperops/workflow/` overlay で吸収する。標準 file 自体を fork する場合だけ `pops detach <path> . --reason "<reason>"` で manifest に登録し、以後の `update-paperops` では手動 rebase 対象として扱う。rebase 後に managed update 対象へ戻す場合は `pops reattach <path> .` を使う。
