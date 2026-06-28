---
name: sync-ja-en
description: 日本語と英語の原稿をブロックレベルで同期する。ブロックが不整合の場合や ja/ セクション編集後に使用。
argument-hint: "[section-file]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# sync-ja-en

Claude Code で使う互換入口。共通手順は `.agents/skills/sync-ja-en/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/sync-ja-en/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- helper files は `.agents/skills/sync-ja-en/` 側を source of truth とし、この wrapper には置かない。
