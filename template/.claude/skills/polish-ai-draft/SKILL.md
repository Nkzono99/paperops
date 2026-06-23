---
name: polish-ai-draft
description: AI 初稿、機械的な文体、過度に定型的なつなぎ、宣伝調、三点列挙、曖昧な出典、AI らしい防御的文章を、主張と証拠を変えずに論文向けに磨くときに使う。
argument-hint: "<file-or-block-id-or-text-scope>"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# polish-ai-draft

Claude Code で使う互換入口。共通手順は `.agents/skills/polish-ai-draft/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/polish-ai-draft/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
