---
name: open-paper-scan
description: 論文プロジェクト、原稿、執筆ハーネスを俯瞰し、発散的な改善案、構造的な違和感、逆張り仮説、未言語化のテーマを出す。ユーザーが「俯瞰的に見て」「meta 的に」「普通に眺めて違和感」「発想を広げたい」「まだ記録や実装はしない」と頼んだとき、または改善指示が局所修正に固着しそうなときに使う。
argument-hint: "<scope-or-artifact>"
allowed-tools: Read, Glob, Grep, Bash
---

# open-paper-scan

Claude Code で使う互換入口。共通手順は `.agents/skills/open-paper-scan/SKILL.md` を source of truth として読む。

@${CLAUDE_SKILL_DIR}/../../../.agents/skills/open-paper-scan/SKILL.md

## Claude Code 実行メモ

- Claude Code 固有の `argument-hint` や `allowed-tools` は、この wrapper の frontmatter で保持する。
- `@` 参照は cwd に依存しないよう `${CLAUDE_SKILL_DIR}` から解決する。
- 読み込まれる `.agents` 側の `Codex 実行メモ` は Codex 向けの補足であり、Claude Code ではこの wrapper の frontmatter と通常の Claude Code tool semantics を優先する。
