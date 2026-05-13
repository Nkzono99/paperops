<!-- harnessops により生成; source records が正本 -->
# 手動評価結果: E0001

送信元: `harness-lab/records/eval-cases/E0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance.md`

## スコア

- impact: 4
- mechanism_clarity: 5
- evaluability: 4
- minimality: 5
- regression_risk: 1
- operator_burden: 1
- anti_theater: 4
- maintainability: 4
- privacy_sanitization_risk: 0

## メモ

harnessops 0.1.6 installed in the paperops venv still lacks the uvx --from harnessops fallback line in packaged Codex and Claude hops-update-harness assets, while the local managed Codex skill includes it. H0001 matches FB0004 and remains reproducible. Guard plan: upstream HarnessOps should add a package asset check that both codex and claude hops-update-harness/SKILL.md contain uvx --from harnessops hops <command>. Kill criteria: reject or revise if runtime docs guarantee hops is always on PATH, or if update-harness preserves additive local guidance without changing packaged assets.

## 評価ケース

- capability: agent-bridge update-harness distribution
- failure_class: packaged-asset-drift
- source_feedback: FB0004
