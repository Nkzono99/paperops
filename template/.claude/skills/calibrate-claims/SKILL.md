---
name: calibrate-claims
description: 原稿の主張強度を evidence strength に合わせる。防御的すぎる文体と過剰主張の両方を調整する。
argument-hint: "[section-or-block-id]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# calibrate-claims

Claude Code で使う互換入口。共通手順は `.agents/skills/calibrate-claims/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/calibrate-claims/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/calibrate-claims/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
