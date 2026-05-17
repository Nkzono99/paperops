---
name: setup
description: テンプレートから作成した新しい論文リポジトリの初回セットアップを一括で行う。プロジェクト開始時に使用。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# setup

Claude Code で使う互換入口。共通手順は `.agents/skills/setup/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/setup/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/setup/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
