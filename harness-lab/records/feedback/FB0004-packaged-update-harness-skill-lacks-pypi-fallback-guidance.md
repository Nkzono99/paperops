---
id: FB0004
record_type: imported_feedback
created_at: '2026-05-13T17:58:49+09:00'
status: triaged
source:
  type: local-capture
  original_id: harness-lab/records/research-scans/RS0001-pypi-hops-agent-asset-drift.md
  source_project: paper-harness-template
classification:
  capability: agent-bridge update-harness distribution
  failure_class: packaged-asset-drift
links:
  eval_case:
  issue_url:
---

# FB0004: Packaged update-harness skill lacks PyPI fallback guidance

## 概要

PyPI harnessops 0.1.4 update-harness produced a .new for .agents/skills/hops-update-harness/SKILL.md that would remove the downstream PyPI fallback instruction. Bridge and compact-memory skills already guide agents to uvx --from harnessops hops <command>, so update-harness should match that distribution model.

## 再現

Run PyPI harnessops 0.1.4 hops update-harness in a linked downstream repo whose hops-update-harness skill includes the uvx --from harnessops fallback line; inspect the generated .new diff.

## 期待する上流変更

Packaged Codex/Claude hops-update-harness skill assets include the PyPI fallback instruction, and update-harness no longer asks downstream maintainers to choose between generated asset text and correct PyPI operation guidance.
