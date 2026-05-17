---
id: E0003
record_type: eval_case
created_at: '2026-05-18T04:25:20+09:00'
status: active
capability: scaffold package boundary hygiene
failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries
source_feedback: FB0006
---

# E0003: FB0006-built-wheel-scaffold-package-boundary-guard を評価

## フィクスチャ

- source_feedback: `harness-lab/records/feedback/FB0006-built-wheel-scaffold-package-boundary-guard.md`
- fixture_dir: `harness-lab/records/eval-cases/fixtures/E0003`
- observation: 一時 wheel build で paperops/_data/scaffold/notes/session-context.generated.md が配布物に含まれる一方、同 wheel の pops init では copy_scaffold の除外により下流には展開されないことを確認した。release artifact 側の境界は acceptance guard がないと再発検知できない。

## タスク

`scaffold package boundary hygiene` の `ignored generated template artifacts can cross release and source-of-truth boundaries` を減らす最小変更を設計または実装し、次の再現条件が解消されるか評価してください。

template/notes/session-context.generated.md が存在する状態で uv build --wheel --out-dir .codex-tmp/priority-20260518-040214-a71d3ef-wheel を実行し、zip contents に paperops/_data/scaffold/notes/session-context.generated.md が含まれることを確認。続けて uvx --from <wheel> pops init .codex-tmp/.../paper-demo を実行し、notes/session-context.generated.md が作成されないことを確認。

## 期待される挙動

wheel 内 scaffold package data と pops init/update の展開結果を検証し、ignored/generated artifact が release artifact に混入しない、または混入しても下流へ出ないことを明示的に守る acceptance smoke を追加する。

## 合格基準

- `ignored generated template artifacts can cross release and source-of-truth boundaries` の再現条件が検出または防止される。
- 提案または実装される変更が source feedback の期待変更に対応している。
- `hops lab eval --case E0003 --manual` の score と notes で採用判断に必要な証拠を説明できる。
- 非公開プロジェクト詳細を追加で要求しない。

## 不合格基準

- `ignored generated template artifacts can cross release and source-of-truth boundaries` の再現条件を見逃す。
- source feedback の期待変更と無関係な改善案になる。
- 評価が yml score へ記録されず、採用判断の証拠として追えない。
- 再現または判断に非公開文脈が必要になる。
