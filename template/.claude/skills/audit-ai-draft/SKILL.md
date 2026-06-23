---
name: audit-ai-draft
description: AI が作った論文初稿を、列挙的な作業報告から主張中心の原稿へ戻すために診断し、論旨設計メモと改稿計画を作る。
argument-hint: "<pdf-or-section-or-scope>"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# audit-ai-draft

Claude Code で使う互換入口。共通手順は `.agents/skills/audit-ai-draft/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/audit-ai-draft/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
