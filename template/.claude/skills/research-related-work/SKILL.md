---
name: research-related-work
description: 関連研究、先行研究、文献レビュー、研究動向、比較対象、反論文献を広く集め、refs/research と refs/summaries と notes/related-work-map.md に整理するときに使う。
argument-hint: "<topic-or-literature-question>"
allowed-tools: Read, Edit, Write, Glob, Grep, WebSearch, Bash
---

# research-related-work

Claude Code で使う互換入口。共通手順は `.agents/skills/research-related-work/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/research-related-work/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
