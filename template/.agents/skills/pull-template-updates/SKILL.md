---
name: pull-template-updates
description: 旧名。上流 paperops scaffold の変更を取り込む場合は update-paperops を使う。
---

# pull-template-updates

このスキルは旧名の互換入口です。新規作業では `/update-paperops` を使う。

実際の手順は `.agents/skills/update-paperops/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- 作業前に `git status`、`git rev-parse --show-toplevel`、対象 remote を確認する。
- nested private repo では親 repo と paper repo の変更を混ぜない。dubious ownership が出たら、まず per-command の `git -c safe.directory=<repo> -C <repo> ...` を使う。
- 下流の原稿・notes・refs のユーザー変更をテンプレート更新で上書きしない。
- `notes/project-brief.md`、`notes/contribution-claims.md`、`notes/related-work-map.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/peer-review.md`、`notes/ai-use.md`、`manuscript/venue.md`、`manuscript/mirror/terminology.yml` はプロジェクト固有内容として扱う。
- 旧テンプレート由来の `docs/project-brief.md`、`docs/target-venue.md`、`docs/contribution-claims.md`、`docs/terminology-ja-en.md` がある場合は、現行パスへ移行する候補として読む。
- 取り込み後は `CHANGELOG.md` の migration note を確認し、必要な `make` ターゲットを実行する。
