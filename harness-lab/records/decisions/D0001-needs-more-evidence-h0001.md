---
id: D0001
record_type: decision
created_at: '2026-05-13T22:09:05+09:00'
status: needs-more-evidence
source: H0001
evidence:
  summary: harness-lab/views/eval-results/E0001-manual-score.yml records current 0.1.6 evidence; IMP0001 investigation notes the packaged Codex/Claude hops-update-harness assets still lack the uvx fallback line.
  guard_path: upstream-harnessops:agent_assets/plugins/{codex,claude}/harnessops/skills/hops-update-harness/SKILL.md contains uvx fallback
---

# D0001: needs-more-evidence H0001

## 判断

needs-more-evidence

## 理由

Manual eval confirms FB0004 remains reproducible in harnessops 0.1.6, but adoption should wait for an upstream HarnessOps asset patch plus guard validation rather than changing paperops local files.

## 証拠

harness-lab/views/eval-results/E0001-manual-score.yml records current 0.1.6 evidence; IMP0001 investigation notes the packaged Codex/Claude hops-update-harness assets still lack the uvx fallback line.

## 回帰リスク

Low for the proposed upstream wording change because it aligns generated assets with existing bridge/compact-memory package execution guidance; remaining risk is over-prescribing PyPI execution for repos that intentionally provide hops on PATH.

## フォローアップ

Patch HarnessOps upstream packaged Codex/Claude hops-update-harness assets and add a guard that checks both generated SKILL.md files contain uvx --from harnessops hops <command>; kill if runtime/docs guarantee hops is always on PATH or update-harness preserves additive local guidance without asset changes.

## 回帰ガード

upstream-harnessops:agent_assets/plugins/{codex,claude}/harnessops/skills/hops-update-harness/SKILL.md contains uvx fallback
