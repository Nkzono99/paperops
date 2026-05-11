---
name: review-public-manuscript
description: Codex で節単位・週次・投稿前の公開原稿を外部読者視点でレビューする。
---

# review-public-manuscript

Codex で使う互換入口。実際の手順は `.claude/skills/review-public-manuscript/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- PDF または公開原稿だけをレビュー入力とし、`notes/`、`refs/local/`、working output は読まない。
- 1 節を書いた直後は `section`、週次では Abstract + Introduction + title candidates + figure/table captions の `weekly`、投稿前は PDF/投稿対象 TeX 全体の `pre-submit` として扱う。
- モード指定がない場合は入力粒度から推定し、出力冒頭で `Review mode` を明記する。
- ユーザーが独立 subagent を明示的に許可した場合だけ、公開アーティファクトのみを渡して別文脈レビューを依頼する。
- `general-researcher`、`reader-assumptions`、`local-terminology`、`public-reproducibility` の観点を明示された場合は、通常の scientific review と別枠で出力する。
- run label、directory name、simulator flag、analysis artifact name、figure label が公開読者に通じる physical condition / public data product として説明されているか確認する。
- 未定義語、ローカル語、暗黙前提、再現性ギャップ、図表 cleanup、Data availability 追記、rewrite patch plan、対応チェックリストに分けて返す。
- repo-aware editor と public-only reviewer を混ぜず、public-only review は読者が詰まる箇所の検出に限定する。修正実装や内部台帳反映は通常の repo 文脈で行う。
