---
name: update-refs
description: 参考文献と参照知識の整合性を検証する。引用の追加や bib ファイル編集後に使用。
allowed-tools: Read, Edit, Write, Glob, Grep
---

# update-refs

Claude Code で使う互換入口。共通手順は `.agents/skills/update-refs/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/update-refs/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
- `.claude/skills/update-refs/` 配下に helper files がある場合は、既存の相対パス互換のためにそのまま利用する。
