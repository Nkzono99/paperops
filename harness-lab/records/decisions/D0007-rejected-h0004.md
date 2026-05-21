---
id: D0007
record_type: decision
created_at: '2026-05-22T04:30:40+09:00'
status: rejected
source: H0004
evidence:
  summary: "E0004 manual score recorded the reproduced mismatch: review context returned 'hops lab investigate --from RS0012', while lab investigate rejected research_scan sources before any RS0012 investigation could be recorded."
  guard_path:
---

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
