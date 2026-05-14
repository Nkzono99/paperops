---
name: resolve-local-paths
description: refs/links.toml と refs/local/ から外部 project、directory、図のソース、外部知識のローカルパスエイリアスを解決する。
allowed-tools: Read, Glob
---

# resolve-local-paths

執筆セッションでリポジトリ外に保存された RunOps project、一般 directory、シミュレーション出力、図のソース、外部知識にアクセスする必要がある場合にこのスキルを使用する。

## 読み込むファイル

- `refs/local/locations.toml`（存在する場合）
- なければ `refs/local/locations.example.toml`
- `refs/local/aliases.md`
- `refs/links.toml`
- `refs/links.md`

## 責務

1. `refs/links.toml` の `alias` と `local_path_alias` を対応付け、要求された link がどの外部 project / directory を指すか説明する。
2. `local_path_alias` を `refs/local/locations.toml` から具体的なパスに解決する。存在しない場合は `locations.example.toml` を参照して、ユーザーが作成すべき alias を示す。
3. パスがマシン固有か、registry metadata がポータブルかを明示する。
4. 使用履歴を記録すべき notes、refs summary、または registry entry を提案する。

個人の絶対パスをトラッキング対象ファイルにコミットしないこと。
