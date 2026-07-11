# CLAUDE.md

ユーザーとは日本語でコミュニケーションする。

このリポジトリは `paperops` から作成された個別論文プロジェクトである。人間が主に触る面は prompt、`story/`、`manuscript/`、`submission/`、レビューコメントである。AI が執筆に使う evidence、claims、refs、requests、workflow、contracts、notes/views は `_paperops/` に置く。

## 基本ルール

- `pops` は `uvx --from paper-harness-cli pops ...` で実行する。
- `CLAUDE.md` は paperops-managed core である。論文固有の恒久指示は `CLAUDE.project.md` に置き、標準ハーネス改善として汎用化できるものは `/feedback-paper-harness` で upstream へ戻す。
- project 固有の tracked Make target は `Makefile.project`、個人環境だけの target や変数は ignored な `Makefile.local` に置く。
- managed core file をどうしても project fork にする場合は、編集理由を `pops detach <path> . --reason "<reason>"` で `.pops/manifest.toml` に登録する。detached file は `update-paperops` の自動更新候補から外れ、手動 rebase 後に `pops reattach <path> .` で管理対象へ戻す。
- 人間は主に原稿レビュー、自然文の指示、story seed の判断を出す。Agent は必要に応じて `/integrate-writing-feedback` で `_paperops/review/` の feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
- `story/` は人間向けの構想層である。研究質問、初期メカニズム仮説、期待する evidence path、結果が外れた場合の分岐を書く。
- `_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` はカード正本である。
- `_paperops/notes/views/` は pure overview view と controlled authoring view を含む。`view_type` と `source_of_truth` を確認し、`pure_overview` はカード総覧、`controlled_authoring` は本文語彙・条件名・読者順序の統制 view として扱う。
- `_paperops/defaults/schemas/registry.yml` と JSON Schema は paperops-managed、`_paperops/model/editorial/editorial-model.yml` と `results-hierarchy.yml` は project-owned の Editorial Model state であり混同しない。`make schema-check` は schema / references / semantics / hash phases を advisory に検査する。authority 切替前は明示的な `python scripts/check-paperops-models.py --root . --model editorial --strict` を成功させ、P2 までは legacy controlled view と既存 checker を維持する。P1-B の Research / Manuscript / Issue / Publication Model、全 model cross-reference、dependency hash は未提供である。
- `_paperops/defaults/contracts/` は paperops-managed の標準 section / figure story 契約であり、文章テンプレートではない。論文固有の契約差分だけ `_paperops/contracts/` に同名 overlay として置く。論文種別や投稿先の上書きは `manuscript/writing-profile.yml` に置く。
- `_paperops/workflow/` は現在状態、review loop、stale 伝播、人間判断の状態正本である。標準の状態機械、focus policy、subagent roster は `_paperops/defaults/workflow/` にあり、本文編集前に `pops workflow status` を確認する。
- subagent を使う執筆では通常 `/develop-manuscript-content` または `/finish-manuscript` から必要時に `orchestrate-manuscript-subagents` へ委譲し、main agent は orchestrator として brief、privacy、integration decision、カード反映を管理する。
- `_paperops/` の作業用ドキュメントは日本語で書く。citation key、TOML field name、外部ツール名は英語のままでよい。
- raw PDF、未整理ファイル、個人環境の絶対パス、confidential reviewer correspondence は tracked file へ混ぜない。
- `_handoff/` は人間から AI への一時受け取り箱であり、内容は Git 管理しない。
- `_archives/` は sealed scratch archive である。通常の執筆・レビュー・関連研究では読まず、明示的な restore / inspect / compare 指示がある場合だけ扱う。
- 生成されたコンテンツは、明示的にスターターや共有すべき成果物でない限り Git 管理しない。

## よく使うコマンド

```sh
uvx --from paper-harness-cli pops doctor
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops links check

make ci
make audit
make pre-submit
make paper-layer-card-check
make card-coverage-check
make workflow-check
make concept-term-check
make authoring-intent-check
make predicted-results-check
make content-first-check
make schema-check
make section-contract-check
make section-depth-check
make finish-manuscript-check
make submission-gate
make figure-reference-check
make figure-obligation-check
```

`make ci` は構造と壊れやすい不整合の確認、`make audit` は執筆品質の advisory check、`make pre-submit` は投稿・外部共有前の厳しめ確認に使う。`manuscript/` は living authoring source であり、投稿後や査読後も編集してよい。投稿用の submission candidate / round snapshot は `submission/` と `_paperops/workflow/submission-ledger.yml` に記録し、`make finish-manuscript-check` で claim-evidence drift を、`make submission-gate` で予測稿、open AREQ、`xx`、AI intent、submission drift を strict に落とす。`authoring-intent-check` は、AI Writer が執筆意図、後で埋める内容、作業計画を公開本文へ漏らしていないか確認する。TeX 環境がない場合、ビルド系 helper は構造検証へフォールバックする。

## 執筆フロー

1. `/resume-session` で前回の状態を読む。
2. `story/story-seed.md` で高次ストーリーを確認する。
3. 必要なら `/map-result-patterns` で raw result や figure data を `_paperops/evidence/` の card にする。
4. 外部 export bundle を使う場合は `_paperops/refs/imports/README.md` に従って import state を確認する。
5. Abstract、Conclusion、main figure caption に使う主張は `/scientific-gate` で readiness を確認する。
6. 原稿内容を進めるときは `/develop-manuscript-content` を入口にし、claims、storyline、figure story、section compiler、予測稿、block-flow review、本文 prose を扱う。Results は `_paperops/model/editorial/results-hierarchy.yml` の `RHI-*` ID と `next_item_id` chain を `python scripts/check-section-contracts.py --root . --strict` で確認してから本文へ変換する。`/finish-manuscript` は投稿可能状態までの監督入口として使う。
7. 図表が本文の主張を支える場合は `/plan-figure-story` を入口にし、必要な個別図だけ `design-paper-figure` や `figure-story-audit` へ進める。
8. 未実行だが投稿前に現実的に実施できる追加シミュレーションがあり、期待結果の根拠を書ける場合は `/develop-manuscript-content` 内の予測稿 route で扱う。本文内には `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:` を置き、`xx` と `_paperops/requests/analysis/` を実データ置換まで追跡する。
9. DRAFTED section は block flow を見直してから AUDITED 扱いにする。直接 `review-block-flow` を呼ぶのは、block 構成の再設計が明示された場合に限る。
10. subagent を使う場合、main agent は orchestrator として role brief と integration decision を `_paperops/review/rounds/` に残す。通常は `/develop-manuscript-content` または `/finish-manuscript` から必要時に委譲する。
11. AI Writer の執筆意図、判断保留、後で埋める内容は本文 prose に書かず、近傍の `% INTENT:` または `% TODO-PAPER:` コメントに置く。解決できない場合は `_paperops/notes/` または `_paperops/requests/` へ移す。公開本文として意図的に扱う場合だけ、直前に `% paperops: allow-authoring-intent -- reason` を置く。
12. 強い英語名詞句や hyphen / slash compound は `_paperops/notes/views/concept-terms.md` に記録し、残す語・普通の文へほどく語・避ける語を分ける。
13. 図表を主図に入れる場合は、caption だけでなく本文側から `\ref{fig:...}` で narrative に接続する。
14. `manuscript/ja/` を中心に書き、必要な block を `manuscript/en/` へ同期する。
15. 人間レビューやプロンプト指示は `/integrate-writing-feedback` で上流カードと原稿へ反映し、必要なら `route-manuscript-feedback`、`pops workflow route-review`、`pops workflow invalidate <artifact-id>` で戻る深さと stale section を更新する。
16. Submission hygiene と投稿メタデータは STRUCTURE_ACCEPTED 後にだけ主作業にする。ORCID、affiliation、license などの記入は `/develop-manuscript-content` では扱わず、投稿前に `/submission-gate` と `make submission-gate`、`make pre-submit` で確認する。完了前は `finalize-manuscript` と `make finish-manuscript-check`、共有前は `make ci` と `make audit` を実行する。投稿後や査読後の修正は `manuscript/` の revision-authoring に戻し、提出済み round snapshot は編集しない。

## スキル入口

- 初回セットアップ・更新: `/setup`, `/update-paperops`
- セッション再開・記録: `/resume-session`, `/note-writing-session`
- 関連研究・外部 source: `/source-reach-scan`, `/research-related-work`, `/update-refs`, `/resolve-local-paths`。summary で済む文献と source card に昇格する文献を分ける。
- 証拠・主張: `/map-result-patterns`, `/scientific-gate`, `/design-manuscript-claims`, `/calibrate-claims`
- AI 初稿診断: `/audit-ai-draft`, `/contextualize-conditions`, `/polish-ai-draft`
- 原稿調整: `/paragraph-surgery`, `/public-terminology-pass`, `/sync-ja-en`
- 通読レビュー: `/start-manuscript-review`, `/collect-manuscript-review`, `/integrate-writing-feedback`
- 査読: `/review-public-manuscript`, `/peer-review-manuscript`, `/respond-to-peer-review`
- 原稿完成の主入口: `/develop-manuscript-content`, `/finish-manuscript`, `/route-manuscript-feedback`, `/submission-gate`
- 原稿完成の内部 route（通常は `/finish-manuscript` から呼ばせる）: `content-first-gate`, `orchestrate-manuscript-subagents`, `compile-results-section`, `compile-discussion-section`, `compile-methods-section`, `draft-predicted-results`, `review-block-flow`, `finalize-manuscript`
- 投稿前点検: `/plan-figure-story`, `/venue-fit-review`, `/ai-disclosure-check`, `/submission-gate`。個別図と監査は `plan-figure-story` から `design-paper-figure` / `figure-story-audit` へ進める。
- アーカイブ・書き直し: `/archive-scratch`
- 俯瞰・改善: `/open-paper-scan`, `/design-paper-storyline`, `/feedback-paper-harness`

Claude Code では `.claude/skills/` の wrapper から `.agents/skills/` の同名 skill を入口として使う。恒久的な手順変更は `.agents/skills/<skill>/SKILL.md` を更新する。

## ディレクトリ

```text
story/                         人間向けの構想、story seed、上位ストーリーライン
CLAUDE.project.md              project-owned の Claude Code 向け恒久指示
Makefile.project               project-owned の tracked Make target
manuscript/                    日英原稿、共有アセット、ミラー制御、投稿先情報
submission/                    投稿先公式テンプレートと最終提出用 TeX
_paperops/                     AI/ハーネス内部 state
_paperops/defaults/            paperops-managed の標準 contract、schema、workflow kernel
_paperops/model/editorial/     project-owned の typed editorial state
_paperops/contracts/           project 固有の contract overlay
_paperops/workflow/            現在状態、review loop、stale 伝播、人間判断、任意の workflow overlay
_paperops/refs/                文献、外部 source、外部 link、import state、local path alias
_paperops/evidence/            result / figure / source card
_paperops/claims/              claim / scientific gate / argument card
_paperops/review/              feedback / review round / block-flow review / response card
_paperops/requests/            analysis / writing request card
_paperops/notes/views/         pure overview view と controlled authoring view
_paperops/notes/               AI 利用、再現性、handoff、decision log
_handoff/                      未整理ファイルの一時受け取り箱
_archives/                     sealed scratch archive
.agents/skills/                Codex 用 project skill
.claude/skills/                Claude Code 用 wrapper
scripts/                       検証、ビルド、ミラー、レビュー回収 helper
```
