---
name: import-manuscript
description: Codex で既存 LaTeX 原稿を paper harness 構造にインポートする。
---

# import-manuscript

Codex で使う互換入口。実際の手順は `.claude/skills/import-manuscript/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 既存原稿の `main.tex`、class/style、bib、figures、投稿先テンプレート assets を分けて棚卸しする。
- `manuscript/ja` / `manuscript/en` のミラー原稿と投稿先固有ファイルを混ぜない。
- インポート後は `make lint-bib`、`make mirror-check`、可能なら build ターゲットを実行する。
