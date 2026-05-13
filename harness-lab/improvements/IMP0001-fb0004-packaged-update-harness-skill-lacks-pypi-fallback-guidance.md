---
id: IMP0001
record_type: improvement_dossier
created_at: '2026-05-13T17:59:14+09:00'
updated_at: '2026-05-13T17:59:30+09:00'
status: active
source_type: friction
scope: harnessops-core
maturity: investigated
relation: extends
promotion_level: candidate
source_feedback: FB0004
eval_cases: []
hypotheses: []
decisions: []
research_scans: []
classification:
  capability: agent-bridge update-harness distribution
  failure_class: packaged-asset-drift
guard:
  status: not-defined
  path:
investigation:
- created_at: '2026-05-13T17:59:23+09:00'
  kind: codebase
  summary: 'RS0001 shows the conflict is specific: generated hops-update-harness asset lacks the PyPI fallback line, while bridge and compact-memory assets already point agents to uvx --from harnessops hops <command>. The local paperops flow now depends on PyPI package execution and venv-installed hops, so this is an upstream packaged asset alignment issue rather than a paperops-only customization.'
  evidence_ref: harness-lab/records/research-scans/RS0001-pypi-hops-agent-asset-drift.md
links:
  issue_url:
---

# IMP0001: FB0004: Packaged update-harness skill lacks PyPI fallback guidance

## Status

- status: active
- maturity: investigated
- source_type: friction
- scope: harnessops-core
- relation: extends
- promotion_level: candidate
- source_feedback: `FB0004`
- linked_records: `FB0004`

## Source Observation

Source: `harness-lab/records/feedback/FB0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance.md`

# FB0004: Packaged update-harness skill lacks PyPI fallback guidance

## 概要

PyPI harnessops 0.1.4 update-harness produced a .new for .agents/skills/hops-update-harness/SKILL.md that would remove the downstream PyPI fallback instruction. Bridge and compact-memory skills already guide agents to uvx --from harnessops hops <command>, so update-harness should match that distribution model.

## 再現

Run PyPI harnessops 0.1.4 hops update-harness in a linked downstream repo whose hops-update-harness skill includes the uvx --from harnessops fallback line; inspect the generated .new diff.

## 期待する上流変更

Packaged Codex/Claude hops-update-harness skill assets include the PyPI fallback instruction, and update-harness no longer asks downstream maintainers to choose between generated asset text and correct PyPI operation guidance.

## Target Capability

- capability: agent-bridge update-harness distribution
- failure_class: packaged-asset-drift

## Investigation

- 2026-05-13T17:59:23+09:00 [codebase] RS0001 shows the conflict is specific: generated hops-update-harness asset lacks the PyPI fallback line, while bridge and compact-memory assets already point agents to uvx --from harnessops hops <command>. The local paperops flow now depends on PyPI package execution and venv-installed hops, so this is an upstream packaged asset alignment issue rather than a paperops-only customization. (evidence: harness-lab/records/research-scans/RS0001-pypi-hops-agent-asset-drift.md)

## Research Scans

research scan はまだありません。


## Evaluation

評価ケースはまだありません。


## Hypotheses

仮説はまだありません。


## Evidence

評価結果はまだありません。

## Guard

- status: not-defined
- path: None

## Links

- issue_url: 未設定

## Open Questions And Next Action

次の実装または評価ステップは、この dossier と紐づく正規化レコードを更新してから再生成してください。

## Decision Log

判断レコードはまだありません。
