---
name: review-public-manuscript
description: Codex で投稿前原稿を外部読者視点でレビューする。
---

# review-public-manuscript

Codex で使う互換入口。実際の手順は `.claude/skills/review-public-manuscript/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- PDF または公開原稿だけをレビュー入力とし、`notes/`、`refs/local/`、working output は読まない。
- ユーザーが独立 subagent を明示的に許可した場合だけ、公開アーティファクトのみを渡して別文脈レビューを依頼する。
- `general-researcher`、`reader-assumptions`、`local-terminology`、`public-reproducibility` の観点を明示された場合は、通常の scientific review と別枠で出力する。
- run label、directory name、simulator flag、analysis artifact name、figure label が公開読者に通じる physical condition / public data product として説明されているか確認する。
- 未定義語、ローカル語、暗黙前提、再現性ギャップ、図表 cleanup、Data availability 追記、rewrite patch plan、対応チェックリストに分けて返す。
