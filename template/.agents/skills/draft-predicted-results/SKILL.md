---
name: draft-predicted-results
description: Use when manuscript writing is blocked by missing but feasible additional simulations, expected quantitative results, placeholder xx values, predicted figures, or pressure to turn absent data into Future Work or defensive prose before submission.
---

# draft-predicted-results

未実行だが投稿前に現実的に実施できる追加シミュレーションを、Future Work や defensive な caveat に逃がさず、検証待ちの予測稿として本文設計に組み込む。予測稿は evidence ではなく、`analysis-needed` の claim を読者向け構造へ先に仮配置するための作業 scaffold である。

## 原則

- 投稿締切が固定でないなら、必要な追加シミュレーションは Future Work ではなく投稿前 blocker として扱う。
- 予測稿は `ready-to-write` ではない。Abstract、Conclusion、title、main figure caption、投稿版では、実データへ置換されるまで使わない。
- 予測稿は必ず TeX comment で未検証状態を明示する。本文 prose だけに `xx` や予測解釈を置かない。
- 追加シミュレーションは現実的、または既存 run / parameter sweep / analysis script の延長線上である必要がある。
- 予測の根拠は、既存 run の傾向、保存則、scaling、pilot result、文献拘束、モデル上の単調性など、後で検証できるものに限る。

## 使わない場合

- 追加実験を実施する見込みがない。
- 結果の符号や相対順位が claim を根本的に反転しうる。
- 新しい solver、未検証 physics、未知の入力データ取得が必要で、既存の延長線上ではない。
- 予測が「こうだったらよい」という希望だけで、EXPECTATION-BASIS が書けない。

## 入力

- 対象 claim / section / `% block:` ID
- `_paperops/claims/gates/` の gate status と `must_not_claim`
- `_paperops/evidence/results/` と `_paperops/notes/views/result-pattern-map.md`
- `_paperops/requests/analysis/` の既存 request
- `_paperops/refs/links.toml` と runops / simulation project link
- Figure を含む場合は `design-paper-figure` の Figure design brief

## 手順

1. 欠けているものを一文で書く。metric、denominator、unit of analysis、comparison、figure panel、Discussion function のどれが未確定かを分ける。
2. feasibility table を作る。追加シミュレーション、既存条件との差分、必要 walltime / storage、入力変更、出力 artifact、解析 script、失敗時の代替 route を書く。
3. prediction basis を作る。期待される符号、順位、範囲、uncertainty、外れた場合の解釈を、既存 evidence かモデル理由に接続する。
4. `_paperops/requests/analysis/` に analysis request を作成または更新する。Acceptance criteria には artifact、metric / estimand、denominator、validated scope、not covered、result card update を入れる。
5. gate card は `analysis-needed` のままにする。`approved_writing_scope` には「予測稿のみ」「publish 不可」「実データ置換後に再 gate」と書き、`must_not_claim` を更新する。
6. 本文へ予測稿を書く場合、対象 block の直前に次の comment block を置く。

```tex
% PREDICTED-RESULT: 未実行シミュレーションに基づく予測稿。status=analysis-needed; publish=false; request=AREQ-XXXX。
% SIM-REQUEST: 実行する追加シミュレーション、既存 run との差分、必要 artifact。
% EXPECTATION-BASIS: 既存 run / scaling / conservation / literature / pilot result に基づく予測根拠。
% REPLACE-XX: xx の数値、図、uncertainty、caption、claim scope を実データで置換する条件。
```

7. prose では `xx`、`approximately xx`、`Fig. xx` のような placeholder を使ってよい。ただし近傍の comment により未検証であること、必要なシミュレーション、置換対象を明示する。
8. 図を先に設計する場合は、Figure design brief に predicted panel、reader task、expected trend、replacement artifact、acceptance criteria を入れる。実データがない図を final figure として扱わない。
9. Discussion では予測結果が得られた場合の解釈、代替説明、境界、decisive next test を書いてよい。ただし「future work」として弱めるのではなく、投稿前に実行する検証待ちの論理として置く。
10. 実データが得られたら、`xx` と予測 comment を置換し、result / figure card、gate card、claim-evidence view、Figure design brief を更新してから `scientific-gate` を再実行する。

## 出力

- `Missing evidence`: 何が未実行か
- `Feasibility table`: 現実的または既存の延長線上である理由
- `Prediction basis`: 期待される結果と外れた場合の分岐
- `Analysis request`: 作成または更新した `_paperops/requests/analysis/` card
- `Predicted manuscript block`: `% PREDICTED-RESULT:` / `% SIM-REQUEST:` / `% EXPECTATION-BASIS:` / `% REPLACE-XX:` つきの draft
- `Figure design updates`: predicted panel と replacement artifact
- `Gate updates`: `analysis-needed`、`must_not_claim`、再 gate 条件

## Codex 実行メモ

- 予測稿を「弱い limitation」や一般的 Future Work に翻訳しない。投稿前に実行できるなら analysis request として扱う。
- defensive な記述を増やす代わりに、どの追加シミュレーションで claim が閉じるかを明示する。
- 実行不能な追加シミュレーションを前提に本文を書かない。
- `PREDICTED-RESULT` comment がある block は final / accepted 扱いにしない。
- 投稿前に必ず実データへ置換し、`xx`、予測 comment、未解決 request が残っていないことを確認する。
