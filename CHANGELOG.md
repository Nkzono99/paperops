# 変更履歴

## Unreleased

- Sprint 2 の品質チェックとして、公開原稿に残る内部語・禁止語を検出する `scripts/check-public-terms.py` と、supported claim の evidence / scope / manuscript block 対応を確認する `scripts/check-claim-evidence.py` を追加し、`make ci` / `make smoke` に組み込んだ。PR テンプレートに論文品質チェックを追加し、refs summary template で文献サマリーの検証状態を記録できるようにした。あわせて Windows の `make` からも shell script target を実行できるよう、`build-ja` / `build-en` / `export-arxiv` は `bash scripts/...` 経由にした。既存下流リポジトリで取り込む場合は新規 script、Makefile target、PR テンプレート、`refs/summaries/summary-template.md`、`readiness-check.py` の placeholder 追加を反映する必要がある。
- Sprint 1 の即効改善として、`scripts/export-arxiv.sh` が generated figures 不在でも失敗しないようにし、`/pull-template-updates` の古い `docs/` パス参照と `/setup` の `refs/local/locations.toml` 自動作成案内を現行の安全運用へ更新した（#16, #17, #18）。既存下流リポジトリでは任意導入だが、取り込む場合は該当 script と skill の更新、README の setup 案内を反映する必要がある。
- 論文品質ゲートの土台として `notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`.claude/rules/writing-quality.md` を追加し、`manuscript/mirror/terminology.yml` を public terminology gate 形式に拡張した（#19, #20, #21）。既存下流リポジトリでは任意導入だが、取り込む場合は新規 notes/rule、`terminology.yml` schema、`readiness-check.py` の追加 placeholder チェック、AGENTS/CLAUDE/README の案内更新が必要。
- TeX 直編集レビューの導線として `/start-manuscript-review` と `/collect-manuscript-review` を追加し、`scripts/collect-manuscript-review.py` で `git diff` と `% REVIEW:` / `% AI:` / `% Q:` / `% KEEP?:` / `% TODO-PAPER:` を `notes/reviews/review-YYYY-MM-DD.md` に回収できるようにした（#15）。既存下流リポジトリでは任意導入だが、この運用を使う場合は新しい skill、script、`.claude/settings.json` の追加許可、AGENTS/CLAUDE/README の案内を取り込む必要がある。
- Manubot、Quarto journal templates、rrtools を一時クローンして参考にし、下流論文リポジトリ向けに `make readiness-check` / `make pre-submit`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md`、原稿レビュー・エビデンス不足・ハーネス摩擦の Issue フォームを追加。既存下流リポジトリでは任意導入だが、共有・投稿前の運用に使う場合は新規ファイルをコピーし、`Makefile` と PR テンプレートを更新する必要がある。
- TeX 本文中の `\cite{...}` / `\citep{...}` 等が `.bib` に存在するかを確認する `scripts/check-citations.py` と `make citation-check` を追加し、`make ci` / `make smoke` に組み込んだ。既存下流リポジトリで取り込む場合は `scripts/check-citations.py` と `Makefile` の target 更新が必要。
- `latexmk -output-directory` 使用時に bibtex が共有 `.bib` を解決できない問題を修正。`BIBINPUTS` / `BSTINPUTS` を設定し、スターター原稿の `\bibliography{}` は `references,mypapers` のようなベース名指定に変更（#7）。既存下流リポジトリでは `\bibliography{../shared/bib/...}` の接頭辞を外す必要がある。
- Windows / PowerShell から PDF をビルドする `scripts/build-ja-pdf.ps1` と `scripts/build-en-pdf.ps1` を追加。pinned Tectonic を `.tools/` に取得し、`-NoDownload` でネットワーク取得を禁止できる（#9）。
- Codex 用に `template/.agents/skills/` を追加し、既存 `.claude/skills/` を source of truth とする同名 skill の互換入口を提供（#12）。
- 投稿先公式テンプレートと最終提出用 TeX を `submission/<venue>/` に分離する標準スロットを追加し、build output と投稿用ローカルツールを ignore（#10）。
- 投稿前原稿を外部読者視点でレビューする `/review-public-manuscript` skill を追加。公開原稿だけを入力に、未定義語、再現性ギャップ、追加解析候補、対応チェックリストを抽出する（#8）。
- nested private paper repo 運用と Windows の dubious ownership / `safe.directory` 対応を `TROUBLESHOOTING.md`、AGENTS/CLAUDE、template 更新 skill に追記（#11）。
- 作業報告型の原稿を主張中心の論文構造へ再設計する `/design-manuscript-claims` skill を追加。主張、証拠、補助解析、対照、限界を分け、必要時のみ block ID 単位の rewrite plan に進む（#13）。
- `/review-public-manuscript` に一般研究者視点の `reader-assumptions` / `local-terminology` / `public-reproducibility` チェックを追加。公開原稿だけでローカル語、実装語、図表ラベル、件数内訳、Data availability の暗黙前提を検出できるようにした（#14）。

## 0.3.0 - 2026-04-14

- `tex-env.example.toml` と `scripts/tex-env.sh` を追加: ユーザー空間 TeX Live や Docker ビルドに対応するための TeX 環境抽象化層（#6）
- ビルドスクリプト（`build-ja.sh`、`build-en.sh`）を `tex-env.sh` に統合し、Docker モードと改善されたフォールバックメッセージを追加（#6）
- `frontmatter/` プレースホルダーに投稿先クラスで不要な場合の案内コメントを追加（#6）
- `journal.cls` がスターター用であることを明記するコメントを追加（#6）
- `/setup` スキルを追加: 初回プロジェクトセットアップ（venv 作成、設定ファイル生成、ワークフロー設定、メタデータ記入）を一括実行（#6）

## 0.2.0 - 2026-04-14

- 全ドキュメント・スキル・ルール・スクリプトのユーザー向けテキストを日本語化
- protect-files フックを廃止し、settings.json の deny パターン + rules/ による保護に移行
- validate-mirror フックを廃止（`make mirror-check` で手動実行に変更）
- SessionStart フックを廃止（`/resume-session` スキルに統合）
- `pull-template-updates` スキルを追加（上流テンプレート変更の下流取り込み）
- AGENTS.md を CLAUDE.md と同一内容に統一
- `git add` / `git commit` を permissions.allow に追加
- bib ファイルからダミーエントリを除去（コメントのみに）
- `/import-manuscript` スキルを追加（既存原稿のインポート支援）
- `docs/` を情報フローに沿って再配置: project-brief, contribution-claims → `notes/`、target-venue → `manuscript/venue.md`、writing-policy → `.claude/rules/`
- README のみのプレースホルダディレクトリ 17 個を削除、refs/ 構造をフラット化
- 用語管理を `manuscript/mirror/terminology.yml` に統一（`docs/terminology-ja-en.md` を廃止）
- `notes/session-context.md` と `notes/writing-log.md` を廃止（generated 版と handoff.md で代替）

## 0.1.0 - 2026-04-13

- `paper-template` リポジトリ構造を初期化
- ビルド、ミラー検証、リリースパッケージング用の再利用可能 GitHub ワークフローを追加
- Issue フォームとテンプレート保守スキルを追加
- `template/` 配下に下流論文スキャフォールド一式を追加
