---
name: calibrate-claims
description: 原稿の主張強度を evidence strength に合わせる。防御的すぎる文体と過剰主張の両方を調整する。
---

# calibrate-claims

原稿の claim strength を evidence、scope、limitation に合わせて調整する。

## 最初に読むファイル

- `_paperops/notes/views/scientific-gate.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/claims/claims/`
- `_paperops/claims/gates/`
- `_paperops/notes/reviewer-model.md`
- `manuscript/mirror/status.md`
- 対象の `manuscript/ja/**/*.tex` と必要な `manuscript/en/**/*.tex`

## 手順

1. 対象 block の claim、evidence、scope、remaining uncertainty を特定する。
2. `_paperops/notes/views/scientific-gate.md` で claim の gate status を確認する。`analysis-needed` や `assumption-blocked` の claim は、hedge だけで本文に通さず、必要な確認へ戻す。
3. hedge を分類する:
   - scope qualifier: 条件・対象範囲を限定する語
   - evidence qualifier: 証拠強度を示す語
   - mechanism qualifier: 因果機構の未確定性を示す語
   - vague hedge: 主張責任を曖昧にするだけの語
4. 証拠が十分な箇所は、`may`, `might`, `could`, `suggest` に逃げず、scope を明示して言い切る。
5. 証拠が局所的な条件集合に依存する場合は、`may suggest` に逃げず、`この条件軸では`、`tested boundary conditions では`、`この保持仮定の範囲では` のように scope を明示して言い切る。
6. limitation は claim 文に混ぜすぎず、後続文または boundary claim として分離する。
7. `_paperops/claims/claims/` と `_paperops/claims/gates/` の status、scope、limitation を必要に応じて更新し、`_paperops/notes/views/claim-evidence-map.md` と `_paperops/notes/views/scientific-gate.md` を俯瞰用に更新する。

## 出力

- 調整した claim
- 弱めすぎを直した箇所
- 過剰主張を抑えた箇所
- 更新した claim / gate card と `claim-evidence` view 項目
- 検証コマンド

本文を編集したら `make mirror-check` を実行し、EN mirror に影響がある場合は `/sync-ja-en` を使う。

## Codex 実行メモ

- `_paperops/claims/claims/`、`_paperops/claims/gates/`、`_paperops/notes/views/scientific-gate.md`、`_paperops/notes/views/claim-evidence-map.md`、`_paperops/notes/reviewer-model.md`、`manuscript/mirror/status.md` を先に読む。
- 防御的すぎる hedge と過剰主張の両方を点検する。
- 条件数が少ない証拠は、弱い主張なのか境界条件として鋭い証拠なのかを分ける。
- 本文を編集したら `make mirror-check`、必要なら `/sync-ja-en` を実行する。
