---
name: submission-gate
description: Use before external sharing, journal submission, resubmission, or response package preparation to turn a living manuscript authoring source into a strict submission candidate.
argument-hint: "[venue-or-round]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# submission-gate

Claude Code で使う互換入口。共通手順は `.agents/skills/submission-gate/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/submission-gate/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
