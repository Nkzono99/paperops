---
name: calibrate-claims
description: Codex で原稿の主張強度を evidence、scope、limitation に合わせて調整する。
---

# calibrate-claims

Codex で使う互換入口。実際の手順は `.claude/skills/calibrate-claims/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`manuscript/mirror/status.md` を先に読む。
- 防御的すぎる hedge と過剰主張の両方を点検する。
- 本文を編集したら `make mirror-check`、必要なら `/sync-ja-en` を実行する。
