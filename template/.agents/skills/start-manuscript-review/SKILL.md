---
name: start-manuscript-review
description: Codex で manuscript review セッションを開始し、レビュー用 branch と人間向けの TeX 通読ガイドを用意する。
---

# start-manuscript-review

Codex で使う互換入口。実際の手順は `.claude/skills/start-manuscript-review/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- まず `git rev-parse --show-toplevel`、`git remote -v`、`git status --short --branch`、`manuscript/mirror/status.md` を確認する。
- clean な作業ツリーなら `review/manuscript-YYYY-MM-DD` またはユーザー指定名へ `git checkout -b` で移動する。
- 未コミット変更がある場合は、勝手に stash / commit / branch 移動をしない。
- ユーザーには `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% TODO-PAPER:` の inline comment と `% block:` 保持ルールを短く案内する。
- レビュー終了後は `/collect-manuscript-review` で diff と inline comment を回収するよう案内する。
