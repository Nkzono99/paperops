---
name: plan-figure-story
description: 本文生成前に中心 claim から必要図表と visual obligation を設計し、missing figure を検出する。
argument-hint: "[claim-or-section]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# plan-figure-story

Claude Code で使う互換入口。共通手順は `.agents/skills/plan-figure-story/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/plan-figure-story/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
