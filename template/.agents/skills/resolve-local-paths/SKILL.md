---
name: resolve-local-paths
description: Codex で refs/links.toml と refs/local のローカルパスエイリアスを安全に解決する。
---

# resolve-local-paths

Codex で使う互換入口。実際の手順は `.claude/skills/resolve-local-paths/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `refs/local/locations.toml` は個人環境ファイルとして扱い、明示依頼なしに作成・編集しない。
- `refs/links.toml` は共有可能な external link metadata、`refs/local/locations.toml` はその `local_path_alias` のローカル解決先として扱う。
- 共有可能な情報は `refs/links.toml`、`refs/local/aliases.md`、`refs/summaries/`、`notes/` に残し、ローカル絶対パスを原稿や共有ドキュメントへ混ぜない。
