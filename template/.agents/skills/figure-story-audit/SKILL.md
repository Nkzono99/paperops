---
name: figure-story-audit
description: Codex で figure/table の claim, evidence, boundary と本文参照を監査する。
---

# figure-story-audit

Codex で使う互換入口。実際の手順は `.claude/skills/figure-story-audit/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `notes/claim-evidence-map.md` と caption/本文参照を照合する。
- caption が claim, evidence, boundary を示しているか確認する。
- provenance が変わる場合は `notes/reproducibility.md` を更新する。
