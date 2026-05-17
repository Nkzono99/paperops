---
name: calibrate-claims
description: 原稿の主張強度を evidence strength に合わせる。防御的すぎる文体と過剰主張の両方を調整する。
---

# calibrate-claims

原稿の claim strength を evidence、scope、limitation に合わせて調整する。

## 最初に読むファイル

- `notes/claim-evidence-map.md`
- `notes/reviewer-model.md`
- `manuscript/mirror/status.md`
- 対象の `manuscript/ja/**/*.tex` と必要な `manuscript/en/**/*.tex`

## 手順

1. 対象 block の claim、evidence、scope、remaining uncertainty を特定する。
2. hedge を分類する:
   - scope qualifier: 条件・対象範囲を限定する語
   - evidence qualifier: 証拠強度を示す語
   - mechanism qualifier: 因果機構の未確定性を示す語
   - vague hedge: 主張責任を曖昧にするだけの語
3. 証拠が十分な箇所は、`may`, `might`, `could`, `suggest` に逃げず、scope を明示して言い切る。
4. 証拠が弱い箇所は、動詞を曖昧にするのではなく limitation / uncertainty を分離する。
5. `notes/claim-evidence-map.md` の status、scope、limitation を必要に応じて更新する。

## 出力

- 調整した claim
- 弱めすぎを直した箇所
- 過剰主張を抑えた箇所
- 更新した `claim-evidence-map` 項目
- 検証コマンド

本文を編集したら `make mirror-check` を実行し、EN mirror に影響がある場合は `/sync-ja-en` を使う。

## Codex 実行メモ

- `notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`manuscript/mirror/status.md` を先に読む。
- 防御的すぎる hedge と過剰主張の両方を点検する。
- 本文を編集したら `make mirror-check`、必要なら `/sync-ja-en` を実行する。
