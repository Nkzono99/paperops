---
name: design-paper-storyline
description: Use when a manuscript needs a top-level story spine, Results hierarchy, Discussion depth, or an editorial-architect pass before drafting, revision, or final review.
argument-hint: "[manuscript-or-section]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# design-paper-storyline

Claude Code で使う互換入口。共通手順は `.agents/skills/design-paper-storyline/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/design-paper-storyline/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
