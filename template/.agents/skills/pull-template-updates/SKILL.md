---
name: pull-template-updates
description: Codex で上流 paper-harness-template の変更を下流論文リポジトリに取り込む。
---

# pull-template-updates

Codex で使う互換入口。実際の手順は `.claude/skills/pull-template-updates/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 作業前に `git status`、`git rev-parse --show-toplevel`、対象 remote を確認する。
- nested private repo では親 repo と paper repo の変更を混ぜない。dubious ownership が出たら、まず per-command の `git -c safe.directory=<repo> -C <repo> ...` を使う。
- 下流の原稿・notes・refs のユーザー変更をテンプレート更新で上書きしない。
- 取り込み後は `CHANGELOG.md` の migration note を確認し、必要な `make` ターゲットを実行する。
