---
name: review-block-flow
description: Use when a manuscript section has a draft, weak author stance, thin Results or Discussion, frozen block order, or needs block-level move/split/merge/delete/add review before AUDITED or ACCEPTED.
argument-hint: "[section-or-block]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# review-block-flow

Claude Code で使う互換入口。共通手順は `.agents/skills/review-block-flow/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/review-block-flow/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
