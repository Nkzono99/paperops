# 外部 link 台帳

`refs/links.toml` は、この paper draft が参照する外部 project / directory の共有台帳である。ここには portable な link の意味だけを置き、マシン固有の絶対パスは ignored な `refs/local/locations.toml` に分離する。

## スキーマ

各 `[[links]]` entry は以下を持つ:

- `id`: notes や skills から使う安定した link id。
- `kind`: `runops_project`, `directory`, `dataset`, `figure_source`, `knowledge`, `simulation` のいずれか。
- `location_ref`: `refs/local/locations.toml` の `[paths.<location_ref>]` に対応する key。
- `description`: link の用途。
- `paper_roles`: `results`, `figures`, `background`, `discussion`, `reproducibility` など、この paper での役割。
- `access`: `read` または `read_write`。

`kind = "runops_project"` の場合は、利用できるなら `mcp_provider`, `mcp_server`, `mcp_tools`, `paper_request_queue` も記録する。追加解析・図表・実験要望は `requests/analysis/` に paper 側の文脈を残し、`notes/views/research-requests.md` で俯瞰し、`runops.paper.request.draft` で検証してから runops project の `research/paper_requests.toml` へ handoff する。

ローカル絶対パス、秘密情報、未公開データの詳細は `refs/links.toml` に書かない。共有できる結論や文献知識は `refs/summaries/` または `notes/` に残す。

## 作業手順

1. `refs/links.toml` に `[[links]]` entry を追加または更新する。
2. 自分の環境では `refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーし、対応する `[paths.<location_ref>]` の `path` を記入する。
3. セッション中は `/resolve-local-paths` で link を解決する。
4. `uvx --from paper-harness-cli pops links check` または `make links-check` で link 台帳を検証する。
