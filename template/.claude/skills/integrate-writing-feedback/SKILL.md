---
name: integrate-writing-feedback
description: 人間の原稿レビュー、プロンプトでの改稿指示、査読コメント、PDF/TeXへの指摘を feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映するときに使う。
argument-hint: "[feedback-or-review-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# integrate-writing-feedback

Claude Code で使う互換入口。共通手順は `.agents/skills/integrate-writing-feedback/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/integrate-writing-feedback/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
