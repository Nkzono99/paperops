---
name: update-paperops
description: Codex で paperops 更新通知や上流 scaffold 更新を安全に取り込む。
---

# update-paperops

Codex で使う互換入口。実際の手順は `.claude/skills/update-paperops/SKILL.md` を source of truth として読む。

## Codex 実行メモ

- `pops` が更新通知を出した場合は、`uvx --from paper-harness-cli pops update-paperops --plan` で versioned upgrade chain を確認し、必要なら `--apply-chain` を使う。
- 単一 version の管理対象ハーネス差分だけを確認する場合は、`uvx --from paper-harness-cli pops update-paperops --dry-run` を使う。
- `pops` は project-local `.venv` ではなく `uvx --from paper-harness-cli pops ...` で実行する。
- 旧 CLI では `pops update-harness` が互換 alias として残るが、新規案内では `update-paperops` を使う。
- 下流の原稿・notes・refs・submission のユーザー変更をテンプレート更新で上書きしない。
- 取り込み後は `CHANGELOG.md` の migration note を確認し、必要な `make` ターゲットを実行する。
