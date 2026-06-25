# AGENTS.md

ユーザーとは日本語でコミュニケーションする。

このリポジトリは `paperops` から作成された個別論文プロジェクトである。原稿だけでなく、証拠・主張・レビュー・依頼の中間層も保守する。

## 基本ルール

- `pops` は `uvx --from paper-harness-cli pops ...` で実行する。
- 人間は主に原稿レビューや自然文の指示を出す。Agent は必要に応じて `/integrate-writing-feedback` で feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
- `evidence/`、`claims/`、`review/`、`requests/` はカード正本である。`notes/views/` は pure overview view と controlled authoring view を含む。旧 `notes/*.md` の一部は互換ビューとして扱う。
- `notes/views/*.md` の `view_type` と `source_of_truth` を確認し、`pure_overview` はカード総覧、`controlled_authoring` は本文語彙・条件名・読者順序の統制 view として扱う。
- `contracts/` は section と figure story の入出力契約であり、文章テンプレートではない。論文種別や投稿先の上書きは `manuscript/writing-profile.yml` に置く。
- `workflow/` は全体状態、section 状態、issue class、stale 伝播の状態正本である。本文編集前に `pops workflow status` を確認する。
- `refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` の作業用ドキュメントは日本語で書く。citation key、TOML field name、外部ツール名は英語のままでよい。
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
make workflow-check
make concept-term-check
make figure-reference-check
make figure-obligation-check
```

`make ci` は構造と壊れやすい不整合の確認、`make audit` は執筆品質の advisory check、`make pre-submit` は投稿・外部共有前の厳しめ確認に使う。TeX 環境がない場合、ビルド系 helper は構造検証へフォールバックする。

## 執筆フロー

1. `/resume-session` で前回の状態を読む。
2. 今日扱う claim、evidence、feedback、request を確認する。
3. 必要なら `/map-result-patterns` で raw result や figure data を evidence card にする。
4. 外部 export bundle を使う場合は `refs/imports/README.md` に従って import state を確認する。
5. Abstract、Conclusion、main figure caption に使う主張は `/scientific-gate` で readiness を確認する。
6. Writer の前に、`pops workflow status`、`contracts/`、`manuscript/writing-profile.yml` を確認し、`/plan-figure-story` で visual obligation と主図構成を決める。その後、必要な card と controlled authoring view から `paper_ir` を作り、Results / Discussion / Methods の section compiler で読者向け構造へ変換する。
7. 強い英語名詞句や hyphen / slash compound は `notes/views/concept-terms.md` に記録し、残す語・普通の文へほどく語・避ける語を分ける。
8. 図表を主図に入れる場合は、caption だけでなく本文側から `\ref{fig:...}` で narrative に接続する。
9. `manuscript/ja/` を中心に書き、必要な block を `manuscript/en/` へ同期する。
10. 人間レビューやプロンプト指示は `/integrate-writing-feedback` で上流カードと原稿へ反映し、必要なら `pops workflow route-review` と `pops workflow invalidate <artifact-id>` で戻る深さと stale section を更新する。
11. 共有前に `make ci` と `make audit`、投稿前に `make pre-submit` を実行する。

## スキル入口

- 初回セットアップ・更新: `/setup`, `/update-paperops`
- セッション再開・記録: `/resume-session`, `/note-writing-session`
- 関連研究・外部 source: `/source-reach-scan`, `/research-related-work`, `/update-refs`, `/resolve-local-paths`
- 証拠・主張: `/map-result-patterns`, `/scientific-gate`, `/design-manuscript-claims`, `/calibrate-claims`
- AI 初稿診断: `/audit-ai-draft`, `/contextualize-conditions`, `/polish-ai-draft`
- 原稿調整: `/paragraph-surgery`, `/public-terminology-pass`, `/sync-ja-en`
- 通読レビュー: `/start-manuscript-review`, `/collect-manuscript-review`, `/integrate-writing-feedback`
- 査読: `/review-public-manuscript`, `/peer-review-manuscript`, `/respond-to-peer-review`
- 投稿前点検: `/plan-figure-story`, `/figure-story-audit`, `/venue-fit-review`, `/ai-disclosure-check`
- 俯瞰・改善: `/open-paper-scan`, `/feedback-paper-harness`

Codex では `.agents/skills/` の同名 skill を入口として使う。恒久的な手順変更は `.agents/skills/<skill>/SKILL.md` を更新する。

## ディレクトリ

```text
manuscript/          日英原稿、共有アセット、ミラー制御、投稿先情報
contracts/           section と figure story の読者質問、入力、出力、禁止構造
workflow/            全体状態、section 状態、review loop、stale 伝播
submission/          投稿先公式テンプレートと最終提出用 TeX
refs/                文献、外部 source、外部 link、import state、local path alias
_handoff/            未整理ファイルの一時受け取り箱
_archives/           sealed scratch archive
evidence/            result / figure / source card
claims/              claim / scientific gate / argument card
review/              feedback / review round / response card
requests/            analysis / writing request card
notes/views/         pure overview view と controlled authoring view
notes/               project brief、読者モデル、AI 利用、再現性、handoff、decision log
.agents/skills/      Codex 用 project skill
.claude/skills/      Claude Code 用 wrapper
scripts/             検証、ビルド、ミラー、レビュー回収 helper
```
