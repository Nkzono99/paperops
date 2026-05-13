# CLAUDE.md

ユーザーとは**日本語**でコミュニケーションすること。

これは**日英バイリンガル論文執筆ハーネス**である。日本語と英語の原稿はブロックレベルのミラーとして追跡される。

## セッションプロトコル

### 開始時

1. `/resume-session` を実行する。
2. 初回セッションの場合は `notes/project-brief.md` を読む。
3. 原稿テキストを編集する前に `manuscript/mirror/status.md` を確認する。

### 終了時

1. `/note-writing-session` を実行する。
2. 原稿構造や参考文献が変更された場合は `make ci` を実行する。

### コンパクション時

セッションコンテキストは PreCompact フックにより自動的に再注入される。コンパクション後、タスクの継続性が必要な場合は `notes/handoff.md` と `notes/todo.md` を再読する。

## 主要コマンド

```sh
pops setup          # .pops と project-local .venv/pops を準備
pops doctor         # ハーネス状態を診断
make venv           # Python 3.11 以上で .venv を作成
make build-ja       # 日本語原稿をコンパイル（または構造検証）
make build-en       # 英語原稿をコンパイル（または構造検証）
make lint-bib       # 参考文献エントリを検証
make lint-bib-pre-submit # 引用済み key に refs/summaries の検証サマリーがあるか検証
make citation-check # TeX の citation key が .bib に存在するか検証
make mirror-check   # ja/ と en/ のブロックレベルのドリフトを検出
make mirror-freshness-check # 前回同期 ledger から ja/en block の更新を検出
make public-terms-check # 公開原稿に内部語・禁止語が残っていないか検証
make claim-evidence-check # supported claim に証拠と本文対応があるか検証
make submission-drift-check # submission/<venue> と manuscript/en の同期注意点を検出
make skill-mirror-check # .agents/skills と .claude/skills の対応を検証
make ci             # lint-bib + citation-check + mirror-check + mirror-freshness-check + public-terms-check + claim-evidence-check + skill-mirror-check + build-ja + build-en
make readiness-check # 公開メタデータ、再現性メモ、workflow 参照の未記入を検出
make pre-submit     # ci + lint-bib-pre-submit + submission 必須 readiness + submission-drift-check
make export-arxiv   # 英語原稿を arXiv 投稿用にバンドル
```

Windows / PowerShell では、PDF 確認用に pinned Tectonic を `.tools/` へ取得する wrapper を使える:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-ja-pdf.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-en-pdf.ps1
```

ネットワーク取得を禁止する場合は `-NoDownload` を付ける。

## ルール

- `manuscript/mirror/status.md` に別段の記載がない限り、`manuscript/ja/` が科学的なソースオブトゥルースである。
- `% block: ...` 識別子を保持する。削除や番号の振り直しは行わない。
- 保護されたファイルを直接編集しない: `manuscript/shared/figures/generated/**`、`refs/local/locations.toml`、`manuscript/shared/style/journal.cls`（settings.json の deny パターンが強制する）。
- `refs/` は**知識層**である。生の PDF よりキュレーション済みのサマリーを優先する。raw PDF は既定で ignore される `refs/papers/` に留め、引用キーは安定させる。
- 投稿先公式テンプレートや最終提出用 TeX は `submission/<venue>/` に置き、`manuscript/ja,en` のミラー原稿と混ぜない。
- 公開・投稿前には `manuscript/publication-metadata.toml`、`notes/reproducibility.md`、`notes/ai-use.md` を更新し、`make pre-submit` を実行する。
- 新しい主張は `notes/claim-evidence-map.md` に evidence、scope、limitation とともに記録する。
- 想定読者や投稿先制約が変わったら `notes/reviewer-model.md` と `manuscript/venue.md` を更新する。
- 内部 run label、script name、directory name、artifact name を本文の公開語として使わず、必要な置換を `manuscript/mirror/terminology.yml` に記録する。
- 1 節を書いた直後や週次の節目では `/review-public-manuscript` を `section` / `weekly` として使い、repo 内部文脈なしで公開語彙・暗黙前提・figure story を確認する。
- ミラー同期には `/sync-ja-en` を使用する。両言語を盲目的に上書きしない。
- 各セッションの終了時に `notes/handoff.md` と `notes/todo.md` を更新する。
- 恒久的な決定は `notes/decision-log.md` に記録する。

ファイル固有のルールは `.claude/rules/` にあり、対応するパスの編集時に自動的にロードされる。

## Git コミットルール

- git 操作前に `git rev-parse --show-toplevel` と `git remote -v` で対象 repo を確認する。nested private repo 運用では、親 repo と paper repo の変更を同じ commit に混ぜない。
- Windows の dubious ownership では、まず `git -c safe.directory=<repo> -C <repo> ...` の per-command 回避を使う。グローバル `safe.directory` 変更はユーザー判断にする。
- 意味のある作業単位ごとにコミットする。大量の変更を一つのコミットにまとめない。
- コミットメッセージは日本語で、変更の「なぜ」を記述する。
- `git push` は共有状態に影響するため、ユーザーの明示的な指示なしに実行しない。
- `git reset --hard`、`git push --force` 等の破壊的操作は、ユーザーが明示的に求めた場合のみ実行する。

## TeX 環境

ユーザー空間 TeX Live、Docker、または JA / EN ごとの LaTeX engine を使用する場合、`tex-env.example.toml` を `tex-env.toml` にコピーして環境を設定する。`tex-env.toml` がなければ従来通り PATH から `latexmk` を探し、既定の `latexmk -pdf` でビルドする。日本語ドラフトで `uplatex + dvipdfmx` が必要な場合は `[latex.ja]` の `latexmk_mode = "pdfdvi"`、`latex`、`dvipdf` を設定する。

## トラブルシューティング

- コンテキストが長くなったら `/compact` を実行する（目安: 50% 超過時）。
- `make ci` が失敗したら、まず `make lint-bib` と `make mirror-check` を個別に実行して原因を特定する。
- ミラーのドリフトが大量にある場合、`/sync-ja-en` で一括同期せず、セクション単位で対処する。
- 設定の優先順: `.claude/settings.local.json`（個人） > `.claude/settings.json`（プロジェクト） > `~/.claude/settings.json`（グローバル）。
- nested repo や `safe.directory` で迷ったら `TROUBLESHOOTING.md` を確認する。

## 利用可能なスキル

| スキル | 用途 |
|-------|------|
| `/setup` | 初回プロジェクトセットアップを一括実行 |
| `/resume-session` | 現在の状態を要約し、次のステップを提案 |
| `/note-writing-session` | セッション進捗を記録し、引き継ぎファイルを更新 |
| `/sync-ja-en` | 日本語と英語のブロックを同期 |
| `/update-refs` | 参考文献と参照知識の整合性を検証 |
| `/improve-writing-harness` | プロジェクトローカルの摩擦を特定・修正 |
| `/feedback-paper-harness` | 再利用可能な改善を上流ハーネスにフィードバック |
| `/resolve-local-paths` | `refs/local/` からローカルパスエイリアスを解決 |
| `/update-paperops` | pops 更新通知や上流 paperops scaffold の変更を安全に取り込む |
| `/pull-template-updates` | 旧名。新規作業では `/update-paperops` を使う |
| `/import-manuscript` | 既存 LaTeX 原稿をハーネスにインポート |
| `/review-public-manuscript` | section / weekly / pre-submit の粒度で、公開原稿だけを入力に外部読者視点の未定義語・ローカル語・暗黙前提をレビュー |
| `/start-manuscript-review` | TeX 直編集レビュー用 branch を用意し、人間向けの通読ガイドを表示 |
| `/collect-manuscript-review` | TeX diff と inline comment からレビュー台帳を生成し、必要に応じて原稿へ反映 |
| `/design-manuscript-claims` | 作業報告型の原稿を主張中心の構造へ再設計 |
| `/calibrate-claims` | evidence strength に合わせて防御的文体と過剰主張を調整 |
| `/public-terminology-pass` | ローカル語・内部語・未定義略語を公開語へ置換 |
| `/paragraph-surgery` | 段落単位の flow、topic sentence、stress position を整える |
| `/figure-story-audit` | figure/table の claim, evidence, boundary と本文参照を監査 |
| `/venue-fit-review` | 投稿先・読者モデルに対する title/abstract/構成の fit を点検 |
| `/ai-disclosure-check` | AI 利用ログ、投稿先ポリシー、人間検証、開示文案を点検 |

## リポジトリマップ

```
manuscript/ja/       日本語ソース（% block: ID 付きセクション）
manuscript/en/       英語ミラー（対応するブロック ID）
manuscript/shared/   figures, bib, style
manuscript/mirror/   map.toml, block-ledger.yml, terminology.yml, status.md, change-queue.md
manuscript/venue.md  投稿先情報
manuscript/publication-metadata.toml  公開タイトル、著者、ライセンス、build provenance
submission/          投稿先公式テンプレート、最終提出用 TeX
refs/                知識層: summaries, local（papers, bib, excerpts はスキルが必要時に作成）
notes/               project-brief, contribution-claims, claim-evidence-map, reviewer-model, ai-use, reproducibility, handoff, todo, decision-log
scripts/             ビルド、TeX 構造、lint、citation-check、skill 対応、ミラー/鮮度/submission チェック、公開語彙・claim-evidence チェック、レビュー回収、エクスポート、コンテキスト収集
.github/ISSUE_TEMPLATE/ 原稿レビュー、エビデンス不足、ハーネス摩擦の収集フォーム
.claude/             settings.json（権限＋deny）、skills/、rules/、hooks/
.agents/             Codex 用 skills/ 互換入口
TROUBLESHOOTING.md   nested repo と safe.directory の注意
```

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、`/feedback-paper-harness` を使用して `Nkzono99/paperops` にルーティングする。
