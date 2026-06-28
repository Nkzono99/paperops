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
- `_paperops/defaults/contracts/` は paperops-managed の標準 section / figure story 契約であり、文章テンプレートではない。論文固有の契約差分だけ `_paperops/contracts/` に同名 overlay として置く。論文種別や投稿先の上書きは `manuscript/writing-profile.yml` に置く。
- `_paperops/workflow/` は現在状態、review loop、stale 伝播、人間判断の状態正本である。標準の状態機械、focus policy、subagent roster は `_paperops/defaults/workflow/` にあり、本文編集前に `pops workflow status` を確認する。
- subagent を使う執筆では `orchestrate-manuscript-subagents` で `_paperops/defaults/workflow/subagent-roster.yml` と必要な project overlay を読み、main agent は orchestrator として brief、privacy、integration decision、カード反映を管理する。
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
make content-first-check
make section-contract-check
make section-depth-check
make finish-manuscript-check
make figure-reference-check
make figure-obligation-check
```

`make ci` は構造と壊れやすい不整合の確認、`make audit` は執筆品質の advisory check、`make pre-submit` は投稿・外部共有前の厳しめ確認に使う。`authoring-intent-check` は、AI Writer が執筆意図、後で埋める内容、作業計画を公開本文へ漏らしていないか確認する。TeX 環境がない場合、ビルド系 helper は構造検証へフォールバックする。

## 執筆フロー

1. `/resume-session` で前回の状態を読む。
2. `story/story-seed.md` で高次ストーリーを確認する。
3. 必要なら `/map-result-patterns` で raw result や figure data を `_paperops/evidence/` の card にする。
4. 外部 export bundle を使う場合は `_paperops/refs/imports/README.md` に従って import state を確認する。
5. Abstract、Conclusion、main figure caption に使う主張は `/scientific-gate` で readiness を確認する。
6. Writer の前に、`content-first-gate`、`pops workflow status`、`_paperops/defaults/workflow/subagent-roster.yml`、`_paperops/defaults/contracts/`、必要な `_paperops/contracts/` overlay、`manuscript/writing-profile.yml`、`/design-paper-storyline` を確認し、`make content-first-check`、`make section-contract-check`、`make section-depth-check` で次の作業が本文 blocker を減らすこと、Results / Discussion の機能 block と Methods 定義 registry が埋まっていること、Results / Discussion が薄すぎないことを確認する。`section_depth` は JA を `ja_chars`、EN を `en_words` で数える floor であり、水増し target にしない。
7. subagent を使う場合は `orchestrate-manuscript-subagents` で story_architect、evidence_auditor、results_structure_reviewer、discussion_function_reviewer などを reviewer として分け、orchestrator が `_paperops/review/rounds/` に integration decision を残す。
8. `/plan-figure-story` で visual obligation と主図構成を決め、個別図は `/design-paper-figure` で図の設計意図、reader task、takeaway、encoding、denominator、caption、runops handoff を Figure design brief にする。その後、必要な card と controlled authoring view から `paper_ir` を作り、`compile-results-section` / `compile-discussion-section` / `compile-methods-section` で読者向け構造へ変換する。
9. 未実行だが投稿前に現実的に実施できる追加シミュレーションがあり、期待結果の根拠を書ける場合は `/draft-predicted-results` で予測稿を作る。本文内には `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:` を置き、`xx` と `_paperops/requests/analysis/` を実データ置換まで追跡する。
10. DRAFTED section は `/review-block-flow` で block operation table を作り、author stance、reader question、why here、move / split / merge / delete / add を確認してから AUDITED 扱いにする。
11. AI Writer の執筆意図、判断保留、後で埋める内容は本文 prose に書かず、近傍の `% INTENT:` または `% TODO-PAPER:` コメントに置く。解決できない場合は `_paperops/notes/` または `_paperops/requests/` へ移す。公開本文として意図的に扱う場合だけ、直前に `% paperops: allow-authoring-intent -- reason` を置く。
12. 強い英語名詞句や hyphen / slash compound は `_paperops/notes/views/concept-terms.md` に記録し、残す語・普通の文へほどく語・避ける語を分ける。
13. 図表を主図に入れる場合は、caption だけでなく本文側から `\ref{fig:...}` で narrative に接続する。
14. `manuscript/ja/` を中心に書き、必要な block を `manuscript/en/` へ同期する。
15. 人間レビューやプロンプト指示は `/integrate-writing-feedback` で上流カードと原稿へ反映し、必要なら `route-manuscript-feedback`、`pops workflow route-review`、`pops workflow invalidate <artifact-id>` で戻る深さと stale section を更新する。
16. Submission hygiene は STRUCTURE_ACCEPTED 後にだけ主作業にする。完了前は `finalize-manuscript` と `make finish-manuscript-check`、共有前は `make ci` と `make audit`、投稿前は `make pre-submit` を実行する。

## スキル入口

- 初回セットアップ・更新: `/setup`, `/update-paperops`
- セッション再開・記録: `/resume-session`, `/note-writing-session`
- 関連研究・外部 source: `/source-reach-scan`, `/research-related-work`, `/update-refs`, `/resolve-local-paths`。summary で済む文献と source card に昇格する文献を分ける。
- 証拠・主張: `/map-result-patterns`, `/scientific-gate`, `/draft-predicted-results`, `/design-manuscript-claims`, `/calibrate-claims`
- AI 初稿診断: `/audit-ai-draft`, `/contextualize-conditions`, `/polish-ai-draft`
- 原稿調整: `/paragraph-surgery`, `/public-terminology-pass`, `/sync-ja-en`
- 通読レビュー: `/start-manuscript-review`, `/collect-manuscript-review`, `/integrate-writing-feedback`
- 査読: `/review-public-manuscript`, `/peer-review-manuscript`, `/respond-to-peer-review`
- 原稿完成補助: `/finish-manuscript`, `/content-first-gate`, `/orchestrate-manuscript-subagents`, `/route-manuscript-feedback`, `/compile-results-section`, `/compile-discussion-section`, `/compile-methods-section`, `/review-block-flow`, `/finalize-manuscript`
- 投稿前点検: `/plan-figure-story`, `/design-paper-figure`, `/figure-story-audit`, `/venue-fit-review`, `/ai-disclosure-check`
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
_paperops/defaults/            paperops-managed の標準 contract と workflow kernel
_paperops/contracts/           project 固有の contract overlay
_paperops/workflow/            現在状態、review loop、stale 伝播、人間判断、任意の workflow overlay
_paperops/refs/                文献、外部 source、外部 link、import state、local path alias
_paperops/evidence/            result / figure / source card
_paperops/claims/              claim / scientific gate / argument card
_paperops/review/              feedback / review round / response card
_paperops/requests/            analysis / writing request card
_paperops/notes/views/         pure overview view と controlled authoring view
_paperops/notes/               AI 利用、再現性、handoff、decision log
_handoff/                      未整理ファイルの一時受け取り箱
_archives/                     sealed scratch archive
.agents/skills/                Codex 用 project skill
.claude/skills/                Claude Code 用 wrapper
scripts/                       検証、ビルド、ミラー、レビュー回収 helper
```
