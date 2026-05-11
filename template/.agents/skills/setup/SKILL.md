---
name: setup
description: Codex でテンプレート由来の新しい論文リポジトリを初回セットアップする。
---

# setup

Codex で使う互換入口。実際の手順は `.claude/skills/setup/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- Claude 固有の `allowed-tools` は Codex の利用可能な shell / file editing tool に読み替える。
- 編集前に `README.md`、`AGENTS.md`、`notes/project-brief.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/venue.md`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md`、`refs/local/locations.example.toml` を確認する。
- `refs/local/locations.toml` はローカル絶対パスを含みうるため、Codex は自動作成・自動編集せず、ユーザーに copy command と編集方針を提示する。
- Core claim、reader model、AI use log は `notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md` の starter を埋めるか、未定 TODO として残す。
- 初回セットアップ後、可能なら `make ci`、外部共有に近い状態なら `make pre-submit` も実行する。難しい場合は `make lint-bib`、`make citation-check`、`make mirror-check` を個別に実行する。
