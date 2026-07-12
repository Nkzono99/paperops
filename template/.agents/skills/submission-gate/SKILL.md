---
name: submission-gate
description: Use before external sharing, journal submission, resubmission, or response package preparation to turn a living manuscript authoring source into a strict submission candidate.
---

# submission-gate

`manuscript/` は living manuscript / authoring source であり、投稿後や査読後も編集してよい。`submission/` は round snapshot と submission candidate を置く派生面であり、投稿済み snapshot は凍結する。二つを同じ状態軸で扱わない。

## 二軸モデル

Authoring axis:

- `authoring`: `manuscript/` を編集中。`% INTENT:`、`% TODO-PAPER:`、`PREDICTED-RESULT`、`xx`、open AREQ があってよい。
- `prediction-staged`: 追加シミュレーションで閉じられる予測稿がある。`draft-predicted-results`、analysis request、`analysis-needed` gate、`publish=false` が必要。
- `executed`: 追加 simulation / analysis が実行され、artifact、result card、figure card がある。
- `reconciled`: 予測と実結果を照合し、違った場合は Results hierarchy、Discussion functions、claim scope を再設計した。
- `revision-authoring`: 査読後や再投稿前に `manuscript/` へ戻って改稿している。

Submission axis:

- `candidate`: `manuscript/` から投稿用 source / PDF / supplement / response package を作る候補。
- `gated`: `submission-gate` と `make pre-submit` が通った候補。
- `frozen`: source commit、PDF、TeX、metadata、gate report を round snapshot として固定した状態。
- `submitted`: 実際に投稿した状態。
- `under-review`: 査読待ち。`manuscript/` は必要なら次の authoring に戻してよい。
- `revision-candidate`: 査読対応後の再投稿候補。
- `resubmitted`: 改訂稿を投稿済み。

`submission/<venue>/round-1/`、`submission/<venue>/round-2/` のように round snapshot を分け、`_paperops/model/publication/publication-model.yml` に source commit、gate report、submitted artifact、review response を記録する。これは重複ではなく提出物の証跡である。

## Gate

投稿候補では次を残さない。

- `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:`
- `xx`、`Fig. xx`、`approximately xx` などの placeholder
- open AREQ / `analysis-needed` central claim
- AI Writer の authoring intent、TODO、後で埋める内容
- 未解決の major feedback、未同期 mirror、未確認 citation、metadata 不備

最小コマンド:

```sh
python scripts/check-predicted-results.py --root . --scope all --strict
make submission-gate
make pre-submit
```

`make submission-gate` は投稿版としての不備、予測稿、authoring intent、research request handoff、submission drift を strict に見る。`make audit` は authoring source の advisory check であり、予測稿があるだけでは投稿不可とは言わない。

## 運用

1. `manuscript/` の編集を止めず、投稿用に切る時点だけ submission candidate を作る。
2. candidate を作る前に、`draft-predicted-results` の予測稿は実データへ materialize する。実行後は result / figure card、claim-evidence view、gate card、Figure design brief を更新する。
3. 予測と結果が違った場合は、本文を予測に合わせず、negative/null route に従って Results hierarchy と claim scope を再設計する。
4. `submission-gate` で通った artifact を `_paperops/model/publication/publication-model.yml` に記録し、`frozen` 以降の round snapshot を編集しない。
5. 投稿後や査読後の修正は `manuscript/` の `revision-authoring` に戻す。`submission/<venue>/round-1/` は比較用 snapshot として残し、改訂は `round-2` または新しい candidate に出す。
6. 査読コメントは `_paperops/model/issues/rounds/` と `_paperops/model/issues/feedback/` に入れ、`route-manuscript-feedback` で evidence / story / section / prose / submission loop へ戻す。

## 出力

- `Submission gate report`: 実行した gate と結果
- `Authoring status`: `authoring` / `prediction-staged` / `executed` / `reconciled` / `revision-authoring`
- `Submission status`: `candidate` / `gated` / `frozen` / `submitted` / `under-review` / `revision-candidate` / `resubmitted`
- `Round snapshot`: `submission/<venue>/round-...` の source commit、PDF、TeX、supplement、response package
- `Blocking items`: 予測稿、open AREQ、metadata、AI intent、citation、figure、mirror、review blocker

## Codex 実行メモ

- `manuscript/` は authoring source として扱い、予測や不確定性を一切書けない場所にしない。
- `submission/` と external share artifact は submission candidate として扱い、予測稿や `xx` を一切残さない。
- 投稿後に `manuscript/` が変わっても、過去の round snapshot は破壊しない。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
