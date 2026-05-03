---
name: review-public-manuscript
description: Codex で投稿前原稿を外部読者視点でレビューする。
---

# review-public-manuscript

Codex で使う互換入口。実際の手順は `.claude/skills/review-public-manuscript/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- PDF または公開原稿だけをレビュー入力とし、`notes/`、`refs/local/`、working output は読まない。
- ユーザーが独立 subagent を明示的に許可した場合だけ、公開アーティファクトのみを渡して別文脈レビューを依頼する。
- 未定義語、再現性ギャップ、追加解析候補、対応チェックリストに分けて返す。
