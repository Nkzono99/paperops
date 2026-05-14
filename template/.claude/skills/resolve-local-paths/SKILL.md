---
name: resolve-local-paths
description: refs/links.toml と refs/local/ からシミュレーション出力、runops project、図のソース、外部知識のローカルパスエイリアスを解決する。
allowed-tools: Read, Glob
---

# resolve-local-paths

執筆セッションでリポジトリ外に保存された runops project、シミュレーション出力、図のソース、外部知識にアクセスする必要がある場合にこのスキルを使用する。

## 読み込むファイル

- `refs/links.toml`（共有 link 台帳）
- `refs/local/locations.toml`（存在する場合）
- なければ `refs/local/locations.example.toml`
- `refs/local/aliases.md`

## 責務

1. `refs/links.toml` の link id、kind、paper_roles、location_ref を確認する。
2. `location_ref` を `refs/local/locations.toml` または example から具体的なパスに解決し、そこに何があるかを説明する。
3. パスがマシン固有かポータブルかを明示する。
4. `kind = "runops_project"` の場合は、runops MCP / publication export manifest を優先して状態や成果物を調べる方針を提案する。
5. 使用履歴、追加解析、図表、実験要望を記録すべき notes または refs ファイルを提案する。

個人の絶対パスをトラッキング対象ファイルにコミットしないこと。

## 記録先の使い分け

- 共有 link の意味: `refs/links.toml`
- 個人環境の絶対パス: `refs/local/locations.toml`
- 追加解析・図表・実験要望: `notes/research-requests.md`
- 論文本文に使う証拠: `notes/claim-evidence-map.md` と `notes/reproducibility.md`
