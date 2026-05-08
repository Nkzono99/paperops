# 変更履歴

## Unreleased

- `latexmk -output-directory` 使用時に bibtex が共有 `.bib` を解決できない問題を修正。`BIBINPUTS` / `BSTINPUTS` を設定し、スターター原稿の `\bibliography{}` は `references,mypapers` のようなベース名指定に変更（#7）。既存下流リポジトリでは `\bibliography{../shared/bib/...}` の接頭辞を外す必要がある。
- Windows / PowerShell から PDF をビルドする `scripts/build-ja-pdf.ps1` と `scripts/build-en-pdf.ps1` を追加。pinned Tectonic を `.tools/` に取得し、`-NoDownload` でネットワーク取得を禁止できる（#9）。
- Codex 用に `template/.agents/skills/` を追加し、既存 `.claude/skills/` を source of truth とする同名 skill の互換入口を提供（#12）。
- 投稿先公式テンプレートと最終提出用 TeX を `submission/<venue>/` に分離する標準スロットを追加し、build output と投稿用ローカルツールを ignore（#10）。
- 投稿前原稿を外部読者視点でレビューする `/review-public-manuscript` skill を追加。公開原稿だけを入力に、未定義語、再現性ギャップ、追加解析候補、対応チェックリストを抽出する（#8）。
- nested private paper repo 運用と Windows の dubious ownership / `safe.directory` 対応を `TROUBLESHOOTING.md`、AGENTS/CLAUDE、template 更新 skill に追記（#11）。
- 作業報告型の原稿を主張中心の論文構造へ再設計する `/design-manuscript-claims` skill を追加。主張、証拠、補助解析、対照、限界を分け、必要時のみ block ID 単位の rewrite plan に進む（#13）。

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
