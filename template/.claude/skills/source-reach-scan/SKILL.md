---
name: source-reach-scan
description: 外部 Web、GitHub、論文ページ、動画、RSS、SNS、議論サイトなどから情報を集める前に、到達経路、認証、raw 保存先、refs への昇格方針を決めるときに使う。
argument-hint: "<topic-or-source-list>"
allowed-tools: Read, Edit, Write, Glob, Grep, WebSearch, Bash
---

# source-reach-scan

Claude Code で使う互換入口。共通手順は `.agents/skills/source-reach-scan/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/source-reach-scan/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
