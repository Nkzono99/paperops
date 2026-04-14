---
name: resolve-local-paths
description: refs/local/ からシミュレーション出力、図のソース、外部知識のローカルパスエイリアスを解決する。
allowed-tools: Read, Glob
---

# resolve-local-paths

執筆セッションでリポジトリ外に保存されたシミュレーション出力、図のソース、外部知識にアクセスする必要がある場合にこのスキルを使用する。

## 読み込むファイル

- `refs/local/locations.toml`（存在する場合）
- なければ `refs/local/locations.example.toml`
- `refs/local/aliases.md`

## 責務

1. エイリアスを具体的なパスに解決し、そこに何があるかを説明する。
2. パスがマシン固有かポータブルかを明示する。
3. 使用履歴を記録すべき notes または refs ファイルを提案する。

個人の絶対パスをトラッキング対象ファイルにコミットしないこと。
