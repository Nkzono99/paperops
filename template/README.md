# paper-my-topic

`pops init` で作成される個別論文プロジェクトのスターター。

この scaffold では、人間が普段見る面と AI が執筆に使う内部状態を分ける。人間側は prompt、`story/`、`manuscript/`、`submission/`、レビューコメントを主な接点にする。AI/ハーネス側の evidence、claims、refs、requests、workflow、contracts、notes/views は `_paperops/` に置く。

## 初回セットアップ

まず `/setup` を使う。手で進める場合の最小手順は次の通り。

1. リポジトリ名とこの README を実プロジェクト名に合わせる。
2. `uvx --from paper-harness-cli pops setup` と `pops doctor` で `.pops/manifest.toml` と構造を確認する。
3. `_paperops/refs/links.toml` を調整し、個人環境の実パスは ignored な `_paperops/refs/local/locations.toml` に書く。
4. 人間から AI へ渡す未整理ファイルは `_handoff/` に置く。
5. `story/story-seed.md`、`manuscript/venue.md`、`manuscript/publication-metadata.toml` を埋める。
6. 必要なら `tex-env.example.toml` を `tex-env.toml` にコピーして TeX 環境を設定する。

`pops` は `uvx --from paper-harness-cli pops ...` で実行する。プロジェクト用 Python 環境が必要な場合だけ `make venv` を使う。

## 日常の流れ

1. `/resume-session` で前回の状態を読む。
2. `story/story-seed.md` で、研究質問、初期メカニズム仮説、期待する evidence path、結果が外れた場合の分岐を確認する。
3. `pops workflow status` と `pops workflow next` で、全体状態と stale section を確認する。
4. 必要なら `_paperops/defaults/workflow/subagent-roster.yml`、`_paperops/defaults/contracts/`、project 固有の `_paperops/contracts/` overlay、`manuscript/writing-profile.yml` を重ね、`design-paper-storyline`、`make content-first-check`、`make section-depth-check` で story spine、Results hierarchy、Discussion functions、Results / Discussion の薄さ、次の作業が本文 blocker を減らすことを確認する。
5. subagent を使う場合、main agent は orchestrator として role brief と integration decision を `_paperops/review/rounds/` に残す。
6. `plan-figure-story` で本文生成前の visual obligation と主図構成を決め、`paper_ir` と section compiler で Results / Discussion / Methods の読者向け構造を作る。
7. `manuscript/ja/` を中心に書く。
8. 必要な block を `manuscript/en/` に同期する。
9. 人間レビューや自然文の指示は `/integrate-writing-feedback` で feedback card にし、`pops workflow route-review` で戻る深さを決める。
10. Submission hygiene は STRUCTURE_ACCEPTED 後に主作業にする。完了前は `make finish-manuscript-check`、共有前は `make ci` と `make audit`、投稿前は `manuscript/publication-metadata.toml` の `[submission]`、`[open_research]`、`[human_verification]` を埋めて `make pre-submit` を実行する。

## 中間層

- `story/`: 人間が読む高次ストーリーと story seed
- `_paperops/evidence/`: result / figure / source card の正本
- `_paperops/claims/`: claim / scientific gate / argument card の正本
- `_paperops/review/`: feedback / review round / response card の正本
- `_paperops/requests/`: analysis / writing request card の正本
- `_paperops/notes/views/`: `view_type` / `source_of_truth` つきの pure overview view と controlled authoring view
- `_paperops/defaults/contracts/`: paperops-managed の標準 section / figure story 契約
- `_paperops/contracts/`: project 固有の contract overlay
- `_paperops/workflow/`: 現在状態、section 状態、issue class、stale 伝播、人間判断
- `_paperops/defaults/workflow/subagent-roster.yml`: subagent role、delegation contract、orchestrator の integration decision 契約
- `manuscript/writing-profile.yml`: 論文種別・投稿先ごとの overlay と `section_depth` floor。JA は `ja_chars`、EN は `en_words` として数え、長さは target ではなく floor として扱う。

`paper_ir` は card と controlled authoring view から Writer に渡す context を作る生成一時物であり、手書き正本にはしない。

## 情報の置き場所

- `_handoff/`: 人間から AI へ渡す未整理ファイル。内容は Git 管理しない。
- `_archives/`: 1から書き直すための sealed scratch archive。通常の AI 執筆では読まない。
- `_paperops/refs/summaries/`: 採用する文献や外部 source の確認済み要約。
- `_paperops/refs/research/`: 関連研究調査の設計と raw finding。
- `_paperops/refs/source-reach/`: Web、GitHub、動画、RSS、SNS など外部 source channel の調査メモ。
- `_paperops/refs/links.toml`: 共有できる外部 project / directory link の意味。
- `_paperops/refs/imports/`: 外部 export bundle の source index、integrity、claim role、取り込み状態。
- `_paperops/refs/local/locations.toml`: 個人環境の実パス。Git 管理しない。

過去稿を封印して同じ repo で書き直す場合は、`pops scratch restart --yes` を使う。archive だけを作る場合は `pops scratch archive`、既存 archive の確認や復元には `pops scratch list`、`pops scratch inspect`、`pops scratch restore` を使う。archive は `_archives/` に split bundle として置かれ、通常の skill は参照しない。

`_paperops/` に作る作業用ドキュメントは日本語で書く。citation key、TOML field name、外部ツール名などの識別子は英語のままでよい。

## 主要スキル

- `/source-reach-scan`, `/research-related-work`: 外部 source と関連研究を整理する。
- `/map-result-patterns`, `/scientific-gate`: 結果を証拠カードにし、主張として書けるか判定する。
- `/plan-figure-story`: 本文生成前に claim から visual obligation、Figure 1、主図/補足図、missing figure を設計する。
- `/finish-manuscript`: `/goal` で原稿完成まで進め、Writer 前に `_paperops/defaults/workflow/subagent-roster.yml`、`plan-figure-story`、`paper_ir`、section compiler、`section-depth-check` を通す。main agent は orchestrator として subagent の review を統合する。
- `/design-paper-storyline`: 原稿全体の story spine、Results hierarchy、Discussion functions を俯瞰し、Submission hygiene へ逸れる前に本文 blocker を固定する。
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
- `_paperops/defaults/`: paperops-managed の標準 contract と workflow kernel
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
