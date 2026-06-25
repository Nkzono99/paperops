---
name: resolve-local-paths
description: runops ディレクトリリンクや外部 project link を refs/links.toml と refs/local/ から解決する。
---

# resolve-local-paths

執筆セッションでリポジトリ外に保存された runops project、シミュレーション出力、図のソース、外部知識にアクセスする必要がある場合にこのスキルを使用する。特に `refs/links.toml` の `runops-main` から runops ディレクトリリンクを解決し、paper 側の request / evidence / import state へ安全につなぐ入口として使う。

## 読み込むファイル

- `refs/links.toml`（共有 link 台帳）
- `refs/local/locations.toml`（存在する場合）
- なければ `refs/local/locations.example.toml`
- `refs/imports/`（外部 bundle を使う場合）
- `refs/local/aliases.md`
- `refs/links.md`

## 最初に実行する確認

```sh
uvx --from paper-harness-cli pops links list --resolve-local
uvx --from paper-harness-cli pops links check
```

`refs/links.toml` の `runops-main` は、既定の runops project link である。`refs/local/locations.toml` が存在すれば `location_ref = "runops_main"` の実パスを確認し、存在しない場合は `refs/local/locations.example.toml` の schema と `refs/links.toml` の意味だけを説明する。明示依頼なしに `refs/local/locations.toml` を作成・編集しない。

## 責務

1. `refs/links.toml` の link id、kind、paper_roles、location_ref を確認する。
2. `location_ref` を `refs/local/locations.toml` または example から具体的なパスに解決し、そこに何があるかを説明する。
3. パスがマシン固有かポータブルかを明示する。
4. 外部 export bundle を使う場合は `refs/imports/` の import state、source index、integrity manifest、source commit、dirty state、claim role を確認する。
5. `kind = "runops_project"` の場合は、runops MCP / publication export manifest を優先して状態や成果物を調べる方針を提案する。
6. 使用履歴、追加解析、図表、実験要望を記録すべき notes または refs ファイルを提案する。

個人の絶対パスをトラッキング対象ファイルにコミットしないこと。

## runops project の扱い

`kind = "runops_project"` の link では、ローカルパスを直接読みに行く前に、利用可能なら runops MCP の read / inspect / plan tool を優先する。

- 結果・図表候補: `runops.analysis.artifacts`, `runops.survey.summary`, `runops.analysis.plot_columns`
- 論文向け export: `runops.publication.exports.list`, `runops.publication.export.inspect`
- 追加解析・図表・実験要望: `runops.paper.request.draft`, `runops.paper.requests.list`, `runops.paper.request.plan`

追加作業が必要な場合は、まず `requests/analysis/` に paper 側の文脈を残し、`notes/views/research-requests.md` で俯瞰する。runops 側へ渡す前に `runops.paper.request.draft` で候補 request を検証し、`data.valid = true` かつ `existing_queue.duplicate_id = false` の場合だけ `toml_snippet` を採用する。duplicate id warning がある場合は、snippet が返っていても追記せず、別の id で draft し直す。

paper 側 request と linked queue の drift は `make research-request-handoff-check` で確認する。`runops_id = draft:*` は draft staged but not queued、queued ID は linked `paper_request_queue` 内の `[[requests]]` と照合する。投稿前や queue handoff を閉じる前は `python scripts/check-research-request-handoff.py --root . --strict` を使う。

このスキルは runops の run creation、survey expansion、job submit は行わない。必要な場合は runops project 側の明示操作として提案する。

## 記録先の使い分け

- 共有 link の意味: `refs/links.toml`
- 個人環境の絶対パス: `refs/local/locations.toml`
- 追加解析・図表・実験要望: `requests/analysis/` と `notes/views/research-requests.md`
- 外部 bundle の取り込み状態: `refs/imports/` と `make external-import-check`
- 論文本文に使う証拠: `evidence/`、`claims/claims/`、`notes/views/claim-evidence-map.md`、`notes/reproducibility.md`

## Codex 実行メモ

- `refs/links.toml` は共有 link 台帳、`refs/local/locations.toml` は個人環境ファイルとして扱う。
- `refs/local/locations.toml` は明示依頼なしに作成・編集しない。
- 共有可能な情報は `refs/local/aliases.md` や `refs/summaries/` に残し、ローカル絶対パスを原稿や共有ドキュメントへ混ぜない。
- export bundle から図表や CSV を読む前に、`refs/imports/*.toml` が `source_index`、`integrity_manifest`、`claim_evidence_policy`、`must_not_claim` を持つか確認する。
- runops project link では `.claude` 側の手順に従い、`runops.paper.request.draft` で検証してから request handoff する。
