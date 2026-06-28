---
name: review-public-manuscript
description: Use when reviewing public manuscript text for reader assumptions and reproducibility gaps.
argument-hint: "<pdf-or-public-manuscript-path> [section|weekly|pre-submit] [general-researcher|reader-assumptions|local-terminology]"
allowed-tools: Read, Glob, Grep, Bash
---

# review-public-manuscript

Claude Code で使う互換入口。共通手順は `.agents/skills/review-public-manuscript/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/review-public-manuscript/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/review-public-manuscript/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
