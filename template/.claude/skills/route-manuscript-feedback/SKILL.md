---
name: route-manuscript-feedback
description: Use when manuscript feedback, review comments, or revision requests need to be routed before editing prose.
argument-hint: "[feedback-or-round]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# route-manuscript-feedback

Claude Code で使う互換入口。共通手順は `.agents/skills/route-manuscript-feedback/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/route-manuscript-feedback/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
