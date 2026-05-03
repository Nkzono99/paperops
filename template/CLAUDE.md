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
make venv           # Python 3.11 で .venv を作成
make build-ja       # 日本語原稿をコンパイル（または構造検証）
make build-en       # 英語原稿をコンパイル（または構造検証）
make lint-bib       # 参考文献エントリを検証
make mirror-check   # ja/ と en/ のブロックレベルのドリフトを検出
make ci             # lint-bib + mirror-check + build-ja + build-en
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
- `refs/` は**知識層**である。生の PDF よりキュレーション済みのサマリーを優先する。引用キーは安定させる。
- 投稿先公式テンプレートや最終提出用 TeX は `submission/<venue>/` に置き、`manuscript/ja,en` のミラー原稿と混ぜない。
- ミラー同期には `/sync-ja-en` を使用する。両言語を盲目的に上書きしない。
- 各セッションの終了時に `notes/handoff.md` と `notes/todo.md` を更新する。
- 恒久的な決定は `notes/decision-log.md` に記録する。

ファイル固有のルールは `.claude/rules/` にあり、対応するパスの編集時に自動的にロードされる。

## Git コミットルール

- 意味のある作業単位ごとにコミットする。大量の変更を一つのコミットにまとめない。
- コミットメッセージは日本語で、変更の「なぜ」を記述する。
- `git push` は共有状態に影響するため、ユーザーの明示的な指示なしに実行しない。
- `git reset --hard`、`git push --force` 等の破壊的操作は、ユーザーが明示的に求めた場合のみ実行する。

## TeX 環境

ユーザー空間 TeX Live や Docker を使用する場合、`tex-env.example.toml` を `tex-env.toml` にコピーして環境を設定する。`tex-env.toml` がなければ従来通り PATH から `latexmk` を探す。

## トラブルシューティング

- コンテキストが長くなったら `/compact` を実行する（目安: 50% 超過時）。
- `make ci` が失敗したら、まず `make lint-bib` と `make mirror-check` を個別に実行して原因を特定する。
- ミラーのドリフトが大量にある場合、`/sync-ja-en` で一括同期せず、セクション単位で対処する。
- 設定の優先順: `.claude/settings.local.json`（個人） > `.claude/settings.json`（プロジェクト） > `~/.claude/settings.json`（グローバル）。

## 利用可能なスキル

| スキル | 用途 |
|-------|------|
| `/setup` | 初回プロジェクトセットアップを一括実行 |
| `/resume-session` | 現在の状態を要約し、次のステップを提案 |
| `/note-writing-session` | セッション進捗を記録し、引き継ぎファイルを更新 |
| `/sync-ja-en` | 日本語と英語のブロックを同期 |
| `/update-refs` | 参考文献と参照知識の整合性を検証 |
| `/improve-writing-harness` | プロジェクトローカルの摩擦を特定・修正 |
| `/raise-template-feedback` | 再利用可能な改善を上流テンプレートにエスカレート |
| `/resolve-local-paths` | `refs/local/` からローカルパスエイリアスを解決 |
| `/pull-template-updates` | 上流テンプレートの変更を安全に取り込む |
| `/import-manuscript` | 既存 LaTeX 原稿をハーネスにインポート |

## リポジトリマップ

```
manuscript/ja/       日本語ソース（% block: ID 付きセクション）
manuscript/en/       英語ミラー（対応するブロック ID）
manuscript/shared/   figures, bib, style
manuscript/mirror/   map.toml, terminology.yml, status.md, change-queue.md
manuscript/venue.md  投稿先情報
submission/          投稿先公式テンプレート、最終提出用 TeX
refs/                知識層: summaries, local（papers, bib, excerpts はスキルが必要時に作成）
notes/               project-brief, contribution-claims, handoff, todo, decision-log
scripts/             ビルド、lint、ミラーチェック、エクスポート、コンテキスト収集
.claude/             settings.json（権限＋deny）、skills/、rules/、hooks/
.agents/             Codex 用 skills/ 互換入口
```

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、`/raise-template-feedback` を使用して `Nkzono99/paper-harness-template` にルーティングする。
