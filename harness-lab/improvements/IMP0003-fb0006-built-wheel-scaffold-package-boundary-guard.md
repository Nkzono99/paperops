---
id: IMP0003
record_type: improvement_dossier
created_at: '2026-05-18T04:24:19+09:00'
updated_at: '2026-05-18T04:27:36+09:00'
status: parked
source_type: friction
scope: paperops release packaging and scaffold generation
maturity: investigated
relation: extends
promotion_level: candidate
source_feedback: FB0006
eval_cases:
- E0003
hypotheses:
- H0003
decisions:
- D0004
research_scans: []
classification:
  capability: scaffold package boundary hygiene
  failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries
guard:
  status: not-defined
  path:
investigation:
- created_at: '2026-05-18T04:26:17+09:00'
  kind: codebase
  summary: RS0008 の一時 wheel 調査を実行した。template/notes/session-context.generated.md が存在する状態で uv build --wheel を実行すると built wheel の paperops/_data/scaffold/notes/session-context.generated.md に生成 context が含まれた。一方、同 wheel を uvx --from <wheel> pops init で使った下流 scaffold には notes/session-context.generated.md が作成されず、copy_scaffold の EXCLUDED_SCAFFOLD_PATTERNS は init 境界では効いている。未実装の guard は release artifact の package-data 境界と wheel-installed init/update 境界の両方を検査する必要がある。
  evidence_ref: harness-lab/records/research-scans/RS0008-generated-context-needs-a-package-boundary-acceptance-guard.md; harness-lab/views/eval-results/E0003-manual-score.yml
links:
  issue_url:
---

# IMP0003: FB0006: Built wheel scaffold package boundary guard

## Status

- status: parked
- maturity: investigated
- source_type: friction
- scope: paperops release packaging and scaffold generation
- relation: extends
- promotion_level: candidate
- source_feedback: `FB0006`
- linked_records: `FB0006`, `E0003`, `H0003`, `D0004`

## Source Observation

Source: `harness-lab/records/feedback/FB0006-built-wheel-scaffold-package-boundary-guard.md`

# FB0006: Built wheel scaffold package boundary guard

## 概要

一時 wheel build で paperops/_data/scaffold/notes/session-context.generated.md が配布物に含まれる一方、同 wheel の pops init では copy_scaffold の除外により下流には展開されないことを確認した。release artifact 側の境界は acceptance guard がないと再発検知できない。

## 再現

template/notes/session-context.generated.md が存在する状態で uv build --wheel --out-dir .codex-tmp/priority-20260518-040214-a71d3ef-wheel を実行し、zip contents に paperops/_data/scaffold/notes/session-context.generated.md が含まれることを確認。続けて uvx --from <wheel> pops init .codex-tmp/.../paper-demo を実行し、notes/session-context.generated.md が作成されないことを確認。

## 期待する上流変更

wheel 内 scaffold package data と pops init/update の展開結果を検証し、ignored/generated artifact が release artifact に混入しない、または混入しても下流へ出ないことを明示的に守る acceptance smoke を追加する。

## Target Capability

- capability: scaffold package boundary hygiene
- failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries

## Investigation

- 2026-05-18T04:26:17+09:00 [codebase] RS0008 の一時 wheel 調査を実行した。template/notes/session-context.generated.md が存在する状態で uv build --wheel を実行すると built wheel の paperops/_data/scaffold/notes/session-context.generated.md に生成 context が含まれた。一方、同 wheel を uvx --from <wheel> pops init で使った下流 scaffold には notes/session-context.generated.md が作成されず、copy_scaffold の EXCLUDED_SCAFFOLD_PATTERNS は init 境界では効いている。未実装の guard は release artifact の package-data 境界と wheel-installed init/update 境界の両方を検査する必要がある。 (evidence: harness-lab/records/research-scans/RS0008-generated-context-needs-a-package-boundary-acceptance-guard.md; harness-lab/views/eval-results/E0003-manual-score.yml)

## Research Scans

research scan はまだありません。


## Evaluation

### E0003: E0003: FB0006-built-wheel-scaffold-package-boundary-guard を評価


- source: `harness-lab/records/eval-cases/E0003-fb0006-built-wheel-scaffold-package-boundary-guard.md`

- capability: scaffold package boundary hygiene

- failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries

- manual_eval_yml: `harness-lab/views/eval-results/E0003-manual-score.yml`
- manual_eval_md: `harness-lab/views/eval-results/E0003-manual-score.md`
- scores: impact=4, mechanism_clarity=5, evaluability=5, minimality=3, regression_risk=2, operator_burden=2, anti_theater=5, maintainability=4, privacy_sanitization_risk=0
- notes: Priority lane evidence from paperops target repo: template/notes/session-context.generated.md existed before the run; uv build --wheel --out-dir .codex-tmp/priority-20260518-040214-a71d3ef-wheel produced paper_harness_cli-0.2.0-py3-none-any.whl; zip contents included paperops/_data/scaffold/notes/session-context.generated.md, proving release artifact package-data drift is reproducible. Running uvx --from <wheel> pops init .codex-tmp/priority-20260518-040214-a71d3ef-init/paper-demo copied 141 files, excluded 2, and did not create notes/session-context.generated.md, so copy_scaffold currently protects downstream init. The proposed guard is evaluable and worthwhile, but adoption should wait for an implementation that either excludes generated artifacts from the wheel or enforces wheel/install boundary behavior in release smoke.


## Hypotheses

### H0003: H0003: E0003-fb0006-built-wheel-scaffold-package-boundary-guard の仮説


Source: `harness-lab/records/hypotheses/H0003-e0003-fb0006-built-wheel-scaffold-package-boundary-guard.md`


# H0003: E0003-fb0006-built-wheel-scaffold-package-boundary-guard の仮説

## 仮説

paperops の release/prepublish smoke は、generated/ignored scaffold artifact が built wheel の bundled scaffold 境界を越えないこと、かつ wheel 経由の pops init/update で下流へ展開されないことを検証する。

## メカニズム

一時 wheel を build し、zip contents と wheel-installed pops init の出力を同じ acceptance check で比較する。notes/session-context.generated.md など EXCLUDED_SCAFFOLD_PATTERNS に含まれる生成物が package data または下流展開面に混入した場合に失敗させる。

## 最小実装

root tests または release smoke に built wheel scaffold boundary check を追加し、生成 context が存在する fixture/一時状態で wheel contents と pops init 結果を検査する。template source 変更は不要。

## 代替案: 削除または統合

copy_scaffold の除外だけを信頼して release artifact 内の混入を許容し続ける。ただし配布物に source-of-truth でない snapshot が残るため、release 後に境界の意味が読み取りづらくなる。

## 期待される利点

make smoke 後に release build しても、ignored/generated artifact の package boundary drift を publish 前に検出できる。

## 想定される欠点

wheel build を伴う check は通常 unit test より重く、ローカル環境に uv/hatchling の build 経路が必要になる。

## 評価計画

E0003 で template/notes/session-context.generated.md が存在する状態の一時 wheel を作り、zip contents と uvx --from <wheel> pops init の結果を記録する。guard 実装後は同じ条件で生成物が wheel または下流 scaffold に混入しないことを検証する。

## 中止基準

hatchling/package config で force-included template から generated artifact を安定除外できない、または check の実行時間が smoke の許容範囲を超える場合は release-only manual checklist へ縮小する。


## Evidence

`harness-lab/views/eval-results/E0003-manual-score.md`

## Guard

- status: not-defined
- path: None

## Links

- issue_url: 未設定

## Open Questions And Next Action

次の実装または評価ステップは、この dossier と紐づく正規化レコードを更新してから再生成してください。

## Decision Log

### D0004: D0004: parked H0003


Source: `harness-lab/records/decisions/D0004-parked-h0003.md`


# D0004: parked H0003

## 判断

parked

## 理由

RS0008 context がこの priority lane での template/package 実装変更を保留し、まず一時 wheel 調査を求めていたため。調査では wheel 内生成 context 混入が再現し、pops init の下流展開除外は確認済みだが、guard 実装は packaging exclude 方針または release smoke 追加方針の選択が必要。

## 証拠

E0003 manual score recorded at harness-lab/views/eval-results/E0003-manual-score.yml; uv build wheel included paperops/_data/scaffold/notes/session-context.generated.md; uvx --from built wheel pops init did not create notes/session-context.generated.md in the target scaffold.

## 回帰リスク

Medium: package exclude を誤ると scaffold files を欠落させる可能性があり、release smoke 化すると wheel build dependency と実行時間が増える。

## フォローアップ

次 lane で pyproject/hatchling の stable exclude 方法を確認し、root tests または release smoke に built-wheel scaffold boundary guard を実装する。RS0009 はその後に docs/guard integration として扱う。

## 回帰ガード

ガードパスは指定されていません。非採用判断では省略できますが、採用済み判断では必須です。
