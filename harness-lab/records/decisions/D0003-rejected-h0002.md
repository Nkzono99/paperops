---
id: D0003
record_type: decision
created_at: '2026-05-17T04:13:50+09:00'
status: rejected
source: H0002
evidence:
  summary: E0002 manual score recorded at harness-lab/views/eval-results/E0002-manual-score.yml; RS0002 and FB0001-FB0003 demonstrate placeholder-only imports being queued for dossier creation.
  guard_path:
---

# D0003: rejected H0002

## 判断

rejected

## 理由

Do not adopt in this paperops target repository: the mechanism is clear and manually evaluated, but implementation belongs in HOPS core import/review-queue routing.

## 証拠

E0002 manual score recorded at harness-lab/views/eval-results/E0002-manual-score.yml; RS0002 and FB0001-FB0003 demonstrate placeholder-only imports being queued for dossier creation.

## 回帰リスク

Medium: a gate that is too broad could park terse but actionable imported feedback, so implementation needs a positive counterexample fixture.

## フォローアップ

Route IMP0002 upstream for HOPS core implementation, with placeholder-only and terse-actionable fixtures, then replace this target-repo rejection with an adopted core decision if validated.

## 回帰ガード

ガードパスは指定されていません。非採用判断では省略できますが、採用済み判断では必須です。
