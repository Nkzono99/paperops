---
name: design-manuscript-claims
description: Codex で原稿を作業報告型から主張中心の論文構造へ再設計する。
---

# design-manuscript-claims

Codex で使う互換入口。実際の手順は `.claude/skills/design-manuscript-claims/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `review-public-manuscript` とは分けて使う。この skill は `notes/project-brief.md`、`notes/contribution-claims.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`manuscript/mirror/status.md`、JA source of truth を読んで、主張と証拠の階層を設計する。
- 設計した claim / evidence / scope / limitation は、ユーザーが了承した範囲で `notes/claim-evidence-map.md` に反映する。
- 先に abstract、introduction、conclusion、section headings、figure captions を読み、Core claim と Essential results を圧縮する。
- 作業報告 smell、keep/compress/move/cut、over-claiming risk、block ID 単位の rewrite plan を出す。
- ユーザーが rewrite を明示した場合だけ `manuscript/ja/` を編集する。`% block: ...` ID を保持し、EN mirror は `sync-ja-en` の方針で同期する。
