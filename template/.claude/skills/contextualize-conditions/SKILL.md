---
name: contextualize-conditions
description: simulation condition、case count、run inventory を、論文上の claim role、scope、boundary、figure story へ翻訳する。
argument-hint: "[section-or-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# contextualize-conditions

Claude Code で使う互換入口。共通手順は `.agents/skills/contextualize-conditions/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/contextualize-conditions/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
