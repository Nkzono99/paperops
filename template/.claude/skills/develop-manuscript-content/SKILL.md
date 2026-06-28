---
name: develop-manuscript-content
description: Use when Codex needs to draft, expand, restructure, or revise manuscript content itself, including claims, storyline, figures, Results, Discussion, Methods, or prose, while keeping submission metadata and external sharing gates out of scope.
argument-hint: "[from-scratch|revision|section|figure|discussion|results] [optional-target]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# develop-manuscript-content

Claude Code で使う互換入口。共通手順は `.agents/skills/develop-manuscript-content/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/develop-manuscript-content/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
