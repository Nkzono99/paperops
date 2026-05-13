---
id: E0001
record_type: eval_case
created_at: '2026-05-13T18:24:31+09:00'
status: active
capability: agent-bridge update-harness distribution
failure_class: packaged-asset-drift
source_feedback: FB0004
---

# E0001: FB0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance を評価

## フィクスチャ

- source_feedback: `harness-lab/records/feedback/FB0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance.md`
- fixture_dir: `harness-lab/records/eval-cases/fixtures/E0001`
- observation: PyPI harnessops 0.1.4 update-harness produced a .new for .agents/skills/hops-update-harness/SKILL.md that would remove the downstream PyPI fallback instruction. Bridge and compact-memory skills already guide agents to uvx --from harnessops hops <command>, so update-harness should match that distribution model.

## タスク

`agent-bridge update-harness distribution` の `packaged-asset-drift` を減らす最小変更を設計または実装し、次の再現条件が解消されるか評価してください。

Run PyPI harnessops 0.1.4 hops update-harness in a linked downstream repo whose hops-update-harness skill includes the uvx --from harnessops fallback line; inspect the generated .new diff.

## 期待される挙動

Packaged Codex/Claude hops-update-harness skill assets include the PyPI fallback instruction, and update-harness no longer asks downstream maintainers to choose between generated asset text and correct PyPI operation guidance.

## 合格基準

- `packaged-asset-drift` の再現条件が検出または防止される。
- 提案または実装される変更が source feedback の期待変更に対応している。
- `hops eval --case E0001 --manual` の score と notes で採用判断に必要な証拠を説明できる。
- 非公開プロジェクト詳細を追加で要求しない。

## 不合格基準

- `packaged-asset-drift` の再現条件を見逃す。
- source feedback の期待変更と無関係な改善案になる。
- 評価が yml score へ記録されず、採用判断の証拠として追えない。
- 再現または判断に非公開文脈が必要になる。
