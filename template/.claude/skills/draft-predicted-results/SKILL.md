---
name: draft-predicted-results
description: Use when manuscript writing is blocked by missing but feasible additional simulations, expected quantitative results, placeholder xx values, predicted figures, or pressure to turn absent data into Future Work or defensive prose before submission.
argument-hint: "[claim-or-block]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# draft-predicted-results

Claude Code で使う互換入口。共通手順は `.agents/skills/draft-predicted-results/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/draft-predicted-results/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
