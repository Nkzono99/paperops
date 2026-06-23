---
name: peer-review-manuscript
description: Use when 投稿前原稿を peer review、査読者、reviewer 2、meta-review、major/minor comments、accept/revise/reject recommendation の形で厳しく評価するときに使う。
argument-hint: "<pdf-or-manuscript-path> [venue-or-mode]"
allowed-tools: Read, Edit, Write, Glob, Grep, WebSearch, Bash
---

# peer-review-manuscript

Claude Code で使う互換入口。共通手順は `.agents/skills/peer-review-manuscript/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/peer-review-manuscript/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
