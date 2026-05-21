---
id: IMP0004
record_type: improvement_dossier
created_at: '2026-05-22T04:28:25+09:00'
updated_at: '2026-05-22T04:31:25+09:00'
status: rejected
source_type: observation
scope: harnessops-core
maturity: investigated
relation: extends
promotion_level: candidate
source_feedback: FB0007
eval_cases:
- E0004
hypotheses:
- H0004
decisions:
- D0007
research_scans: []
classification:
  capability: hops research scan queue command consistency
  failure_class: research_scan next_command points to unsupported investigate source
guard:
  status: not-defined
  path:
investigation:
- created_at: '2026-05-22T04:28:41+09:00'
  kind: codebase
  summary: review queue/context can emit 'hops lab investigate --from RS0012' for research_scan candidates, but lab investigate resolves dossiers only from FB/E/H/D/IMP sources. The attempted RS0012 command failed before any RS investigation could be recorded, so the supported path is inconsistent with the generated next_command.
  evidence_ref: harness-lab/records/research-scans/RS0012-runops-link-handoff-needs-a-privacy-boundary-preview.md;hops lab investigate --help;hops lab review context --capability external link privacy and handoff visibility --json
links:
  issue_url:
---

# IMP0004: FB0007: Research-scan queue emits unsupported investigate command

## Status

- status: rejected
- maturity: investigated
- source_type: observation
- scope: harnessops-core
- relation: extends
- promotion_level: candidate
- source_feedback: `FB0007`
- linked_records: `FB0007`, `E0004`, `H0004`, `D0007`

## Source Observation

Source: `harness-lab/records/feedback/FB0007-research-scan-queue-emits-unsupported-investigate-command.md`

# FB0007: Research-scan queue emits unsupported investigate command

## 概要

During priority-improvement lane, review queue/context recommended 'hops lab investigate --from RS0012', but current hops lab investigate only accepts FB/E/H/D/IMP sources and fails for research_scan records. This blocks the intended RS0012 pre-implementation investigation path.

## 再現

Run 'uvx --from harnessops hops lab review context --capability external link privacy and handoff visibility --json', then run the returned 'hops lab investigate --from RS0012 ...' command.

## 期待する上流変更

Either support investigation notes directly from research_scan records or make review queue/context emit a supported next command for RS candidates.

## Target Capability

- capability: hops research scan queue command consistency
- failure_class: research_scan next_command points to unsupported investigate source

## Investigation

- 2026-05-22T04:28:41+09:00 [codebase] review queue/context can emit 'hops lab investigate --from RS0012' for research_scan candidates, but lab investigate resolves dossiers only from FB/E/H/D/IMP sources. The attempted RS0012 command failed before any RS investigation could be recorded, so the supported path is inconsistent with the generated next_command. (evidence: harness-lab/records/research-scans/RS0012-runops-link-handoff-needs-a-privacy-boundary-preview.md;hops lab investigate --help;hops lab review context --capability external link privacy and handoff visibility --json)

## Research Scans

research scan はまだありません。


## Evaluation

### E0004: E0004: FB0007-research-scan-queue-emits-unsupported-investigate-command を評価


- source: `harness-lab/records/eval-cases/E0004-fb0007-research-scan-queue-emits-unsupported-investigate-command.md`

- capability: hops research scan queue command consistency

- failure_class: research_scan next_command points to unsupported investigate source

- manual_eval_yml: `harness-lab/views/eval-results/E0004-manual-score.yml`
- manual_eval_md: `harness-lab/views/eval-results/E0004-manual-score.md`
- scores: impact=3, mechanism_clarity=5, evaluability=5, minimality=4, regression_risk=2, operator_burden=1, anti_theater=5, maintainability=4, privacy_sanitization_risk=0
- notes: Priority lane reproduced a concrete HOPS next_command mismatch: review context for RS0012 returns 'hops lab investigate --from RS0012', while the current investigate command rejects research_scan records and only supports FB/E/H/D/IMP-backed dossiers. The fix is narrow and testable with a research_scan queue fixture; implementation belongs in HOPS core, not paperops.


## Hypotheses

### H0004: H0004: E0004-fb0007-research-scan-queue-emits-unsupported-investigate-command の仮説


Source: `harness-lab/records/hypotheses/H0004-e0004-fb0007-research-scan-queue-emits-unsupported-investigate-command.md`


# H0004: E0004-fb0007-research-scan-queue-emits-unsupported-investigate-command の仮説

## 仮説

HOPS review queue/context never emits a next_command for research_scan records that the advertised command cannot execute.

## メカニズム

Align research_scan next commands with supported HOPS entrypoints: either teach lab investigate to attach investigation notes to research_scan records, or change queue/context generation to emit a supported capture/research-scan/retire workflow for RS candidates.

## 最小実装

Add a HOPS core fixture with a research_scan candidate whose next_command is produced by review queue/context, then assert that the emitted command succeeds or is replaced by a supported command.

## 代替案: 削除または統合

Leave RS next_command as aspirational text and require operators to infer a supported workflow manually, but that breaks unattended steward lanes and repeats the failure seen in RS0012.

## 期待される利点

Priority lanes can follow HOPS-provided next commands without falling into command-contract failures, improving autonomous run reliability across target/meta labs.

## 想定される欠点

Supporting direct RS investigations may expand the lab record mutation surface; changing next_command generation is narrower but may preserve less structured investigation history.

## 評価計画

Run E0004 against HOPS core after the fix: generate a research_scan queue/context item, execute the returned next_command, and require the command to complete without creating duplicate RS records or requiring private project context.

## 中止基準

Reject if HOPS intentionally treats research_scan next_command as non-executable prose, or if a supported RS investigation path would require unsafe direct edits to lab records.


## Evidence

`harness-lab/views/eval-results/E0004-manual-score.md`

## Guard

- status: not-defined
- path: None

## Links

- issue_url: 未設定

## Open Questions And Next Action

次の実装または評価ステップは、この dossier と紐づく正規化レコードを更新してから再生成してください。

## Decision Log

### D0007: D0007: rejected H0004


Source: `harness-lab/records/decisions/D0007-rejected-h0004.md`


# D0007: rejected H0004

## 判断

rejected

## 理由

Do not adopt this in the paperops target repository: the failure is a HOPS core command-contract mismatch, and the paperops repo cannot safely implement or guard the CLI behavior locally.

## 証拠

E0004 manual score recorded the reproduced mismatch: review context returned 'hops lab investigate --from RS0012', while lab investigate rejected research_scan sources before any RS0012 investigation could be recorded.

## 回帰リスク

Medium for HOPS core: fixing by broadening investigate could expand mutation semantics; fixing next_command generation is narrower but must preserve useful RS workflows.

## フォローアップ

Route IMP0004 upstream to HOPS core, then retry the RS0012 nonblocking privacy-boundary preview investigation after a supported command path exists.

## 回帰ガード

ガードパスは指定されていません。非採用判断では省略できますが、採用済み判断では必須です。
