---
name: setup
description: Codex でテンプレート由来の新しい論文リポジトリを初回セットアップする。
---

# setup

Codex で使う互換入口。実際の手順は `.claude/skills/setup/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- Claude 固有の `allowed-tools` は Codex の利用可能な shell / file editing tool に読み替える。
- 編集前に `README.md`、`AGENTS.md`、`notes/project-brief.md`、`manuscript/venue.md`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md`、`refs/local/locations.example.toml` を確認する。
- 初回セットアップ後、可能なら `make ci`、外部共有に近い状態なら `make pre-submit` も実行する。難しい場合は `make lint-bib`、`make citation-check`、`make mirror-check` を個別に実行する。
