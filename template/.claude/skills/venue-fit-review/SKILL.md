---
name: venue-fit-review
description: manuscript/venue.md と投稿先・読者モデルに照らして、章立て、title/abstract、scope、必須要件を調整する。
argument-hint: "[venue-or-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# venue-fit-review

Claude Code で使う互換入口。共通手順は `.agents/skills/venue-fit-review/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/venue-fit-review/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/venue-fit-review/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
