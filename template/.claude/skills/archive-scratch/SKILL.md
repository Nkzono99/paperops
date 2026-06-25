---
name: archive-scratch
description: 過去稿を封印して1から書き直す、scratch archive を一覧・確認・復元する、または _archives/ の扱いを判断するときに使う。
allowed-tools: Read, Bash, Glob, Grep
---

# archive-scratch

Claude Code で使う互換入口。共通手順は `.agents/skills/archive-scratch/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/archive-scratch/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
