---
name: map-result-patterns
description: simulation results、figure data、analysis artifact、run output を、本文の主張へ直接流し込む前に result pattern / evidence packet へ抽象化する。ユーザーが「結果と原稿の間の中間層」「結果を論文上の文脈へ整理」「run 結果から主張候補を作る」と頼んだときに使う。
---

# map-result-patterns

raw result、figure data、analysis artifact、run output を、本文や claim に直接入れる前の result pattern へ束ねるために使う。

Quarto manuscripts、showyourwork!、research compendium のような外部ハーネスは、計算・図表・原稿・環境の関係を明示する。paperops ではそれを全面的な DAG や別 authoring system にせず、執筆判断用の薄い中間層として `notes/result-pattern-map.md` に置く。

## 最初に読むファイル

- `notes/result-pattern-map.md`
- `notes/condition-context-map.md`
- `notes/claim-evidence-map.md`
- `notes/argument-map.md`
- `notes/reproducibility.md`
- `refs/links.toml`
- 対象の figure/table、Results section、analysis summary、runops export summary

## 目的

- run inventory や case count を、そのまま本文の主張にしない。
- result を `observed contrast`、`effect direction / magnitude`、`negative or null cases`、`failure mode`、`candidate interpretation` に分解する。
- まだ claim ではない観察単位を `result pattern` として保持する。
- 本文に入れる result story は `evidence packet` として、claim、figure/table、metric、scope、limitation、provenance link に接続する。
- 条件名や denominator は `/contextualize-conditions` の方針で公開文脈へ翻訳する。

## 手順

### 1. Result unit を切り出す

入力された結果から、次の単位を切り出す:

- 同じ比較軸を持つ contrast
- 同じ機構を示す複数の run / condition
- null / negative case を含む境界条件
- robustness を示す設定変更
- exploratory または provenance-only に留める材料

この段階では claim に昇格しない。

### 2. Result pattern にする

各 unit について、`notes/result-pattern-map.md` の `結果パターン inventory` を埋める:

- `observed contrast`
- `effect direction / magnitude`
- `condition groups`
- `negative or null cases`
- `uncertainty / failure mode`
- `candidate interpretation`
- `candidate claim role`
- `next action`

run label、directory、script name、internal export name は raw reference または provenance に留め、本文用の語にしない。

### 3. 条件文脈へ接続する

pattern が条件数、case count、denominator に依存する場合は、`notes/condition-context-map.md` へ渡す:

- local condition ではなく public condition name を付ける
- denominator が読者に意味を持つか確認する
- `0` や少数例を failure / boundary / negative control / insufficient coverage に分ける
- 本文で言ってよい表現と notes-only provenance を分ける

### 4. Evidence packet にする

本文や図表に入れる pattern だけ、`Evidence packet 化する場合` を埋める。

packet は 1 つの result story として扱い、最低限以下を持つ:

- `supported claim ID`
- `figure/table`
- `metric`
- `scope`
- `limitation`
- `manuscript block`
- `reproduce / provenance link`

claim ID が未定なら `C1 / 未定` のように仮置きし、claim として採用する段階で `notes/claim-evidence-map.md` に移す。

### 5. Manuscript routing を決める

各 pattern を以下に分類する:

- `promote to claim`: `claim-evidence-map` に移す
- `figure story`: `figure-story-audit` で caption / 本文参照へ接続する
- `condition context`: `condition-context-map` で公開条件名と scope を整理する
- `supplement`: Methods、supplement、Data availability に退避する
- `notes-only`: 執筆判断や再現性のために残す
- `discard`: 今回の論文の story から外す

## 出力形式

- `Result pattern map`: pattern ID、observed contrast、effect direction、null cases、candidate interpretation
- `Evidence packets`: 本文や図表に入れる result story
- `Condition context handoff`: `/contextualize-conditions` へ渡す条件・denominator
- `Claim promotion candidates`: `claim-evidence-map` へ昇格できる候補
- `Move to supplement / notes`: 本文から退避する材料
- `Risks`: overclaim、coverage 不足、公開語不足、provenance 不足

## 注意事項

- result pattern は claim ではない。claim へ昇格するには evidence、warrant、scope、limitation が必要。
- すべての result を本文に入れない。論文の story を支えない pattern は notes-only または discard にする。
- 外部 project や runops にある結果は、可能なら `refs/links.toml` や export summary を経由し、個人環境の絶対パスを tracked ファイルへ入れない。
- `refs/` と `notes/` の作業用ドキュメントは日本語で書く。

## Codex 実行メモ

- ユーザーが本文編集を明示しない限り、`manuscript/` は編集しない。
- result pattern を作った後に claim へ昇格する場合は、`notes/claim-evidence-map.md` の主張台帳も更新する。
- 図表 caption まで進む場合は `/figure-story-audit`、条件数や denominator の翻訳へ進む場合は `/contextualize-conditions` を使う。
