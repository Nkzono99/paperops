---
id: E0004
record_type: eval_case
created_at: '2026-05-22T04:29:36+09:00'
status: active
capability: hops research scan queue command consistency
failure_class: research_scan next_command points to unsupported investigate source
source_feedback: FB0007
---

# E0004: FB0007-research-scan-queue-emits-unsupported-investigate-command を評価

## フィクスチャ

- source_feedback: `harness-lab/records/feedback/FB0007-research-scan-queue-emits-unsupported-investigate-command.md`
- fixture_dir: `harness-lab/records/eval-cases/fixtures/E0004`
- observation: During priority-improvement lane, review queue/context recommended 'hops lab investigate --from RS0012', but current hops lab investigate only accepts FB/E/H/D/IMP sources and fails for research_scan records. This blocks the intended RS0012 pre-implementation investigation path.

## タスク

`hops research scan queue command consistency` の `research_scan next_command points to unsupported investigate source` を減らす最小変更を設計または実装し、次の再現条件が解消されるか評価してください。

Run 'uvx --from harnessops hops lab review context --capability external link privacy and handoff visibility --json', then run the returned 'hops lab investigate --from RS0012 ...' command.

## 期待される挙動

Either support investigation notes directly from research_scan records or make review queue/context emit a supported next command for RS candidates.

## 合格基準

- `research_scan next_command points to unsupported investigate source` の再現条件が検出または防止される。
- 提案または実装される変更が source feedback の期待変更に対応している。
- `hops lab eval --case E0004 --manual` の score と notes で採用判断に必要な証拠を説明できる。
- 非公開プロジェクト詳細を追加で要求しない。

## 不合格基準

- `research_scan next_command points to unsupported investigate source` の再現条件を見逃す。
- source feedback の期待変更と無関係な改善案になる。
- 評価が yml score へ記録されず、採用判断の証拠として追えない。
- 再現または判断に非公開文脈が必要になる。
