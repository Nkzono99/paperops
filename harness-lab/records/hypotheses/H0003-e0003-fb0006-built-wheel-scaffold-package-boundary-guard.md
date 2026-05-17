---
id: H0003
record_type: hypothesis
created_at: '2026-05-18T04:25:37+09:00'
status: proposed
target_capability: scaffold package boundary hygiene
source_eval_case: E0003
---

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
