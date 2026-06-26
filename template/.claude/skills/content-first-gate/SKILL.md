---
name: content-first-gate
description: Use when manuscript work may drift from content repair into submission hygiene, harness maintenance, or low-impact polish.
argument-hint: "[intent-or-blocker]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# content-first-gate

Claude Code で使う互換入口。共通手順は `.agents/skills/content-first-gate/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/content-first-gate/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
