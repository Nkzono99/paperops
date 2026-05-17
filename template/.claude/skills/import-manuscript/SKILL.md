---
name: import-manuscript
description: 既存の LaTeX 原稿をハーネス構造にインポートする。Overleaf や別リポジトリからの移行時に使用。
argument-hint: "<source-dir>"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# import-manuscript

Claude Code で使う互換入口。共通手順は `.agents/skills/import-manuscript/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/import-manuscript/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/import-manuscript/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
