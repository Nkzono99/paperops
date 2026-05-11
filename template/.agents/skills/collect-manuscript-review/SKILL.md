---
name: collect-manuscript-review
description: Codex で TeX 直編集 diff と inline review comment を回収し、台帳化して必要に応じて原稿へ反映する。
---

# collect-manuscript-review

Codex で使う互換入口。実際の手順は `.claude/skills/collect-manuscript-review/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `git status --short --branch`、`manuscript/mirror/status.md`、`manuscript/mirror/map.toml` を確認する。
- `python scripts/collect-manuscript-review.py --root . --output notes/reviews/review-YYYY-MM-DD.md` で台帳を生成する。
- `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% TODO-PAPER:` を file / line / `% block:` に紐付けて読む。
- 本文反映を依頼されている場合は、まず source-of-truth 側を整え、解決済み inline comment を削除し、必要な `manuscript/en` block を同期する。
- 原稿本文または mirror を変えたら `make mirror-check` を実行する。構造、引用、refs、build に触れた場合は `make ci` を実行する。
