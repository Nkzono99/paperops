---
name: figure-story-audit
description: figure/table が claim, evidence, boundary を支えているか、caption・本文参照・claim-evidence map を監査する。
argument-hint: "[figure-or-section]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# figure-story-audit

Claude Code で使う互換入口。共通手順は `.agents/skills/figure-story-audit/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/figure-story-audit/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/figure-story-audit/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
