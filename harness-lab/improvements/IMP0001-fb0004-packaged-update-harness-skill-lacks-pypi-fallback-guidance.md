---
id: IMP0001
record_type: improvement_dossier
created_at: '2026-05-13T17:59:14+09:00'
updated_at: '2026-05-16T04:11:05+09:00'
status: adopted
source_type: friction
scope: harnessops-core
maturity: validated
relation: extends
promotion_level: adopted
source_feedback: FB0004
eval_cases:
- E0001
hypotheses:
- H0001
decisions:
- D0002
research_scans: []
classification:
  capability: agent-bridge update-harness distribution
  failure_class: packaged-asset-drift
guard:
  status: implemented
  path: .agents/skills/hops-update-harness/SKILL.md
investigation:
- created_at: '2026-05-13T17:59:23+09:00'
  kind: codebase
  summary: 'RS0001 shows the conflict is specific: generated hops-update-harness asset lacks the PyPI fallback line, while bridge and compact-memory assets already point agents to uvx --from harnessops hops <command>. The local paperops flow now depends on PyPI package execution and venv-installed hops, so this is an upstream packaged asset alignment issue rather than a paperops-only customization.'
  evidence_ref: harness-lab/records/research-scans/RS0001-pypi-hops-agent-asset-drift.md
- created_at: '2026-05-13T18:12:39+09:00'
  kind: external-benchmark
  summary: GitHub issue Nkzono99/harnessops#10 is closed with a v0.1.4 fix note saying packaged assets now use uvx fallback. Installed harnessops 0.1.4 confirms bridge, README, and compact-memory assets were updated, but codex/claude hops-update-harness SKILL assets still lack the PyPI fallback line. This narrows FB0004 from a broad distribution issue to a missed asset in the closed fix.
  evidence_ref: https://github.com/Nkzono99/harnessops/issues/10
- created_at: '2026-05-13T18:12:50+09:00'
  kind: codebase
  summary: Installed harnessops 0.1.4 contains uvx fallback text in core/agent_bridge.py and both compact-memory skills, but rg over site-packages shows codex and claude hops-update-harness/SKILL.md list update commands without the fallback instruction. Local paperops kept that line, which is why update-harness wrote a .new that would remove it.
  evidence_ref: .venv/Lib/site-packages/harnessops/agent_assets/plugins/codex/harnessops/skills/hops-update-harness/SKILL.md
- created_at: '2026-05-13T18:24:23+09:00'
  kind: codebase
  summary: PyPI harnessops 0.1.5 still packages codex hops-update-harness/SKILL.md without the PATH/uvx fallback line. Running update-harness in paperops after the 0.1.5 lock update again produced a .new conflict whose only semantic difference was removal of the local uvx fallback guidance, so FB0004 remains reproducible after the 0.1.4 fix note.
  evidence_ref: 'PyPI harnessops 0.1.5: agent_assets/plugins/codex/harnessops/skills/hops-update-harness/SKILL.md'
- created_at: '2026-05-16T04:06:32+09:00'
  kind: codebase
  summary: PyPI harnessops 0.1.11 update-harness --agent-bridge was run in paperops after preflight reported repo managed artifacts at 0.1.10. It updated managed files and five agent bridge skills, added hops-github-flow, and reported conflicted 0 with no .new files. The local hops-update-harness skill retained uvx package execution guidance, so the FB0004 drift condition did not recur on this update.
  evidence_ref: .harnessops/lock.json; .agents/skills/hops-update-harness/SKILL.md; update-harness output 2026-05-16
links:
  issue_url:
---

# IMP0001: FB0004: Packaged update-harness skill lacks PyPI fallback guidance

## Status

- status: adopted
- maturity: validated
- source_type: friction
- scope: harnessops-core
- relation: extends
- promotion_level: adopted
- source_feedback: `FB0004`
- linked_records: `FB0004`, `E0001`, `H0001`, `D0002`

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
- 2026-05-13T18:12:39+09:00 [external-benchmark] GitHub issue Nkzono99/harnessops#10 is closed with a v0.1.4 fix note saying packaged assets now use uvx fallback. Installed harnessops 0.1.4 confirms bridge, README, and compact-memory assets were updated, but codex/claude hops-update-harness SKILL assets still lack the PyPI fallback line. This narrows FB0004 from a broad distribution issue to a missed asset in the closed fix. (evidence: https://github.com/Nkzono99/harnessops/issues/10)
- 2026-05-13T18:12:50+09:00 [codebase] Installed harnessops 0.1.4 contains uvx fallback text in core/agent_bridge.py and both compact-memory skills, but rg over site-packages shows codex and claude hops-update-harness/SKILL.md list update commands without the fallback instruction. Local paperops kept that line, which is why update-harness wrote a .new that would remove it. (evidence: .venv/Lib/site-packages/harnessops/agent_assets/plugins/codex/harnessops/skills/hops-update-harness/SKILL.md)
- 2026-05-13T18:24:23+09:00 [codebase] PyPI harnessops 0.1.5 still packages codex hops-update-harness/SKILL.md without the PATH/uvx fallback line. Running update-harness in paperops after the 0.1.5 lock update again produced a .new conflict whose only semantic difference was removal of the local uvx fallback guidance, so FB0004 remains reproducible after the 0.1.4 fix note. (evidence: PyPI harnessops 0.1.5: agent_assets/plugins/codex/harnessops/skills/hops-update-harness/SKILL.md)
- 2026-05-16T04:06:32+09:00 [codebase] PyPI harnessops 0.1.11 update-harness --agent-bridge was run in paperops after preflight reported repo managed artifacts at 0.1.10. It updated managed files and five agent bridge skills, added hops-github-flow, and reported conflicted 0 with no .new files. The local hops-update-harness skill retained uvx package execution guidance, so the FB0004 drift condition did not recur on this update. (evidence: .harnessops/lock.json; .agents/skills/hops-update-harness/SKILL.md; update-harness output 2026-05-16)

## Research Scans

research scan はまだありません。


## Evaluation

### E0001: E0001: FB0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance を評価


- source: `harness-lab/records/eval-cases/E0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance.md`

- capability: agent-bridge update-harness distribution

- failure_class: packaged-asset-drift

- manual_eval_yml: `harness-lab/views/eval-results/E0001-manual-score.yml`
- manual_eval_md: `harness-lab/views/eval-results/E0001-manual-score.md`
- scores: impact=4, mechanism_clarity=5, evaluability=4, minimality=4, regression_risk=1, operator_burden=1, anti_theater=5, maintainability=4, privacy_sanitization_risk=0
- notes: PyPI harnessops 0.1.11 update-harness --agent-bridge completed in paperops with managed files updated and agent bridge conflicted 0. No *.new files were produced, and .agents/skills/hops-update-harness/SKILL.md still includes uvx package execution guidance. This satisfies the E0001 check for preventing packaged-asset-drift in this linked target repo; remaining risk is external verification in harnessops core packaging history if a release decision is needed.


## Hypotheses

### H0001: H0001: E0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance の仮説


Source: `harness-lab/records/hypotheses/H0001-e0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance.md`


# H0001: E0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance の仮説

## 仮説

Packaged Codex and Claude hops-update-harness skill assets include the same PyPI uvx fallback wording used by other HarnessOps agent bridge assets.

## メカニズム

Align the generated hops-update-harness SKILL.md assets with the package-first execution path: when hops is not on PATH, agents are explicitly told to run uvx --from harnessops hops <command>.

## 最小実装

Patch the bundled codex and claude hops-update-harness skill templates to add the PATH/uvx fallback sentence, then run update-harness in a linked target repo and verify no .new diff removes that local guidance.

## 代替案: 削除または統合

Leave downstream repos to keep local-only wording and manually reject .new files, but that preserves repeated update friction and weakens generated asset trust.

## 期待される利点

Downstream target/project repositories can accept update-harness managed skill assets without losing correct PyPI execution guidance.

## 想定される欠点

If a repo intentionally wants no PyPI fallback guidance, the managed asset becomes slightly more prescriptive, but it matches documented package execution behavior.

## 評価計画

Run E0001 against a linked repo whose local hops-update-harness skill contains the uvx fallback line; after the asset patch, update-harness should not generate a .new file that removes the fallback wording.

## 中止基準

Reject or revise if the package runtime guarantees hops is always on PATH, or if update-harness conflict behavior is changed to preserve additive local guidance without changing packaged assets.


## Evidence

`harness-lab/views/eval-results/E0001-manual-score.md`

## Guard

- status: implemented
- path: .agents/skills/hops-update-harness/SKILL.md

## Links

- issue_url: 未設定

## Open Questions And Next Action

次の実装または評価ステップは、この dossier と紐づく正規化レコードを更新してから再生成してください。

## Decision Log

### D0002: D0002: adopted H0001


Source: `harness-lab/records/decisions/D0002-adopted-h0001.md`


# D0002: adopted H0001

## 判断

adopted

## 理由

PyPI harnessops 0.1.11 の packaged update-harness asset は、paperops target repo で uvx package execution guidance を落とさずに更新できた。

## 証拠

hops update-harness --agent-bridge reported conflicted 0 and no *.new files; E0001 manual score recorded at harness-lab/views/eval-results/E0001-manual-score.yml; lock now records harnessops_version 0.1.11.

## 回帰リスク

Low for paperops: changes are HarnessOps managed bridge assets plus lock metadata. Remaining risk is limited to downstream operators reading new GitHub Flow guidance, covered by doctor/migrate and repo smoke validation.

## フォローアップ

Keep watching future update-harness runs for .new drift; no remote issue action is needed while harnessops#10 remains closed and 0.1.11 verifies cleanly.

## 回帰ガード

.agents/skills/hops-update-harness/SKILL.md
