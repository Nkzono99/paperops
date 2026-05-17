---
name: resolve-local-paths
description: refs/links.toml と refs/local/ からシミュレーション出力、runops project、図のソース、外部知識のローカルパスエイリアスを解決する。
---

# resolve-local-paths

執筆セッションでリポジトリ外に保存された runops project、シミュレーション出力、図のソース、外部知識にアクセスする必要がある場合にこのスキルを使用する。

## 読み込むファイル

- `refs/links.toml`（共有 link 台帳）
- `refs/local/locations.toml`（存在する場合）
- なければ `refs/local/locations.example.toml`
- `refs/local/aliases.md`
- `refs/links.md`

## 責務

1. `refs/links.toml` の link id、kind、paper_roles、location_ref を確認する。
2. `location_ref` を `refs/local/locations.toml` または example から具体的なパスに解決し、そこに何があるかを説明する。
3. パスがマシン固有かポータブルかを明示する。
4. `kind = "runops_project"` の場合は、runops MCP / publication export manifest を優先して状態や成果物を調べる方針を提案する。
5. 使用履歴、追加解析、図表、実験要望を記録すべき notes または refs ファイルを提案する。

個人の絶対パスをトラッキング対象ファイルにコミットしないこと。

## runops project の扱い

`kind = "runops_project"` の link では、ローカルパスを直接読みに行く前に、利用可能なら runops MCP の read / inspect / plan tool を優先する。

- 結果・図表候補: `runops.analysis.artifacts`, `runops.survey.summary`, `runops.analysis.plot_columns`
- 論文向け export: `runops.publication.exports.list`, `runops.publication.export.inspect`
- 追加解析・図表・実験要望: `runops.paper.request.draft`, `runops.paper.requests.list`, `runops.paper.request.plan`

追加作業が必要な場合は、まず `notes/research-requests.md` に paper 側の文脈を残す。runops 側へ渡す前に `runops.paper.request.draft` で候補 request を検証し、`data.valid = true` かつ `existing_queue.duplicate_id = false` の場合だけ `toml_snippet` を採用する。duplicate id warning がある場合は、snippet が返っていても追記せず、別の id で draft し直す。

このスキルは runops の run creation、survey expansion、job submit は行わない。必要な場合は runops project 側の明示操作として提案する。

## 記録先の使い分け

- 共有 link の意味: `refs/links.toml`
- 個人環境の絶対パス: `refs/local/locations.toml`
- 追加解析・図表・実験要望: `notes/research-requests.md`
- 論文本文に使う証拠: `notes/claim-evidence-map.md` と `notes/reproducibility.md`

## Codex 実行メモ

- `refs/links.toml` は共有 link 台帳、`refs/local/locations.toml` は個人環境ファイルとして扱う。
- `refs/local/locations.toml` は明示依頼なしに作成・編集しない。
- 共有可能な情報は `refs/local/aliases.md` や `refs/summaries/` に残し、ローカル絶対パスを原稿や共有ドキュメントへ混ぜない。
- runops project link では `.claude` 側の手順に従い、`runops.paper.request.draft` で検証してから request handoff する。
