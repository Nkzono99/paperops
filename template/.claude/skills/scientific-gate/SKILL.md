---
name: scientific-gate
description: 中心主張、Abstract、Conclusion、主要図表、claim package を書く前に、結果・文献・再現性・人間承認の準備状態を科学的ゲートとして判定するときに使う。
argument-hint: "[claim-id-or-section-or-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, WebSearch, Bash
---

# scientific-gate

Claude Code で使う互換入口。共通手順は `.agents/skills/scientific-gate/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/scientific-gate/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
