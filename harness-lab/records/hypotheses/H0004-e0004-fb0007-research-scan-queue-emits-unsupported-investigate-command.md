---
id: H0004
record_type: hypothesis
created_at: '2026-05-22T04:30:26+09:00'
status: proposed
target_capability: hops research scan queue command consistency
source_eval_case: E0004
---

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
