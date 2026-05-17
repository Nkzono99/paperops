---
id: FB0006
record_type: imported_feedback
created_at: '2026-05-18T04:24:07+09:00'
status: triaged
source:
  type: local-capture
  original_id: RS0008; .codex-tmp/priority-20260518-040214-a71d3ef-wheel; .codex-tmp/priority-20260518-040214-a71d3ef-init
  source_project: paper-harness-template
classification:
  capability: scaffold package boundary hygiene
  failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries
links:
  eval_case:
  issue_url:
---

# FB0006: Built wheel scaffold package boundary guard

## 概要

一時 wheel build で paperops/_data/scaffold/notes/session-context.generated.md が配布物に含まれる一方、同 wheel の pops init では copy_scaffold の除外により下流には展開されないことを確認した。release artifact 側の境界は acceptance guard がないと再発検知できない。

## 再現

template/notes/session-context.generated.md が存在する状態で uv build --wheel --out-dir .codex-tmp/priority-20260518-040214-a71d3ef-wheel を実行し、zip contents に paperops/_data/scaffold/notes/session-context.generated.md が含まれることを確認。続けて uvx --from <wheel> pops init .codex-tmp/.../paper-demo を実行し、notes/session-context.generated.md が作成されないことを確認。

## 期待する上流変更

wheel 内 scaffold package data と pops init/update の展開結果を検証し、ignored/generated artifact が release artifact に混入しない、または混入しても下流へ出ないことを明示的に守る acceptance smoke を追加する。
