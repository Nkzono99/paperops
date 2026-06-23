---
name: respond-to-peer-review
description: Use when editor decision letter、査読コメント、major/minor revision、rebuttal、response to reviewers、revision plan、response matrix を整理して返答案を作るときに使う。
argument-hint: "<decision-letter-or-comments-path>"
allowed-tools: Read, Edit, Write, Glob, Grep, WebSearch, Bash
---

# respond-to-peer-review

Claude Code で使う互換入口。共通手順は `.agents/skills/respond-to-peer-review/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/respond-to-peer-review/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
