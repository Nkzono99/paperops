<!-- harnessops により生成; source records が正本 -->
# 手動評価結果: E0004

送信元: `harness-lab/records/eval-cases/E0004-fb0007-research-scan-queue-emits-unsupported-investigate-command.md`

## スコア

- impact: 3
- mechanism_clarity: 5
- evaluability: 5
- minimality: 4
- regression_risk: 2
- operator_burden: 1
- anti_theater: 5
- maintainability: 4
- privacy_sanitization_risk: 0

## メモ

Priority lane reproduced a concrete HOPS next_command mismatch: review context for RS0012 returns 'hops lab investigate --from RS0012', while the current investigate command rejects research_scan records and only supports FB/E/H/D/IMP-backed dossiers. The fix is narrow and testable with a research_scan queue fixture; implementation belongs in HOPS core, not paperops.

## 評価ケース

- capability: hops research scan queue command consistency
- failure_class: research_scan next_command points to unsupported investigate source
- source_feedback: FB0007
