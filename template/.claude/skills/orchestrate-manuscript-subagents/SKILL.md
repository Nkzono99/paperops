---
name: orchestrate-manuscript-subagents
description: Use when manuscript finishing will delegate review, evidence, story, figure, or submission checks to subagents.
argument-hint: "[role-or-target]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# orchestrate-manuscript-subagents

Claude Code で使う互換入口。共通手順は `.agents/skills/orchestrate-manuscript-subagents/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/orchestrate-manuscript-subagents/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
