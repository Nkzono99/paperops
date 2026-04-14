# AGENTS

このリポジトリはバイリンガル研究論文の執筆ハーネスである。

## ここから開始

1. `docs/project-brief.md` を読む。
2. `notes/session-context.md`、`notes/handoff.md`、`notes/todo.md` を読む。
3. 原稿テキストを編集する前に `manuscript/mirror/status.md` を確認する。

## 基本ルール

- `manuscript/mirror/status.md` に別段の記載がない限り、日本語コンテンツがソースオブトゥルースである。
- すべてのミラー対象セクションで `% block: ...` 識別子を保持する。
- `refs/` は知識層として整理する。生の PDF 置き場にしない。
- 個人の絶対パスはコミットしない。`refs/local/locations.example.toml` と ignored なローカルオーバーライドを使用する。
- 作業セッション終了前に `notes/` を更新する。

## 標準コマンド

- `make build-ja`
- `make build-en`
- `make mirror-check`
- `make lint-bib`
- `make ci`
- `make venv`
