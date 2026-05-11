---
name: public-terminology-pass
description: Codex でローカル語・内部語・未定義略語を公開語へ置換する。
---

# public-terminology-pass

Codex で使う互換入口。実際の手順は `.claude/skills/public-terminology-pass/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `manuscript/mirror/terminology.yml` を gate として使う。
- 本文、figure caption、section heading の local term を public term に置換する。
- 最後に `make public-terms-check` を実行する。
