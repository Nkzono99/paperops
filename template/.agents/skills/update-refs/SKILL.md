---
name: update-refs
description: Codex で参考文献と refs 知識層の整合性を確認・更新する。
---

# update-refs

Codex で使う互換入口。実際の手順は `.claude/skills/update-refs/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `refs/` は生 PDF 置き場ではなく知識層として扱う。
- citation key を安定させ、`manuscript/shared/bib/` と `refs/summaries/` の対応を確認する。
- bib を編集したら `make lint-bib` を実行する。
