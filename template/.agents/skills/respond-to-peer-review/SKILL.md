---
name: respond-to-peer-review
description: Use when editor decision letter、査読コメント、major/minor revision、rebuttal、response to reviewers、revision plan、response matrix を整理して返答案を作るときに使う。
---

# respond-to-peer-review

実際に返ってきた editor / reviewer comments を、感情的な反応ではなく、対応可能な revision plan と response letter に変換する。

## 最初に確認すること

- reviewer letter や editor correspondence は confidential な場合がある。外部検索語にそのまま使わず、tracked notes へ丸写ししない。
- 実査読コメントを AI に処理させてよいか、投稿先・出版社ポリシーとユーザーの明示許可を先に確認する。許可が未確認または不可の場合は、本文や raw comment を読まず、人間が使う response matrix / checklist の雛形だけを出す。
- raw letter は `_handoff/` やユーザーが渡したローカルファイルに置き、`review/feedback/` と `notes/views/peer-review.md` には要約、comment ID、対応方針、変更先だけを残す。
- response draft では、実施していない変更、未確認の line/page number、存在しない追加解析を主張しない。

## 最初に読むファイル

- editor / reviewer comments（ユーザー指定ファイルまたは貼り付け）
- `notes/views/peer-review.md`
- `review/feedback/`
- `review/responses/`
- `notes/views/scientific-gate.md`
- `notes/views/claim-evidence-map.md`
- `notes/views/result-pattern-map.md`
- `notes/related-work-map.md`
- `notes/source-reach.md`
- `notes/reviewer-model.md`
- `notes/reproducibility.md`
- `manuscript/venue.md`
- `manuscript/mirror/status.md`

## 手順

### 1. コメントを ID 化する

reviewer の文脈を壊さず、扱いやすい単位へ分割する。

| ID | source | comment summary | requested change | severity | status |
| --- | --- | --- | --- | --- | --- |
| E-001 | editor | 未記入 | 未記入 | required / optional | open |
| R1-001 | reviewer 1 | 未記入 | 未記入 | major / minor | open |

長いコメントは「主懸念」と「副次的な要望」に分ける。皮肉や曖昧な語調を強めず、reviewer が実質的に求めている判断へ翻訳する。

### 2. 対応方針を分類する

各 comment を以下に分類する:

- `accept-change`: 原稿を直す
- `clarify`: 既存の内容を明確化する
- `add-analysis`: 追加解析・図表・実験が必要
- `add-reference`: 関連研究・引用を追加する
- `rebut`: 原稿の主張を維持し、根拠を示して反論する
- `scope-limit`: 主張の射程を狭める
- `response-only`: 原稿は変えず、response letter で説明する
- `ask-human`: 人間判断が必要

### 3. Response matrix を作る

`review/feedback/` と `notes/views/peer-review.md` に反映する場合は、raw comment ではなく要約で残す。

| comment ID | issue | response stance | manuscript change | evidence / source | owner | status |
| --- | --- | --- | --- | --- | --- | --- |
| R1-001 | 未記入 | accept-change / rebut / clarify | file/block/figure | note/ref/result | human / AI | open |

### 4. Revision plan を作る

修正先を分ける:

- `manuscript/ja/` の本文 block
- figure / caption / table
- `manuscript/shared/bib/` と `refs/summaries/`
- `claims/gates/`
- `claims/claims/`
- `evidence/results/`
- `evidence/figures/`
- `requests/analysis/`
- `notes/reproducibility.md`
- response letter only

本文編集は、ユーザーが「反映して」「修正して」「response を作って本文も直して」と明示した場合だけ行う。編集する場合は `% block: ...` を保持し、EN mirror は `/sync-ja-en` の方針で同期する。

### 5. Response letter を下書きする

各回答は短く、次の順に書く:

1. reviewer の懸念を正しく受け取ったことを示す
2. 変更した場合は何をどこに変更したかを書く
3. 変更しない場合は、根拠と scope を丁寧に説明する
4. 必要なら追加解析・補足・limitation を示す

line/page number は最終レイアウト確定後に入れる。未確定なら section / figure / block で仮置きする。

## 出力

- `Comment inventory`: editor / reviewer ごとの comment ID
- `Triage`: accept / clarify / add-analysis / add-reference / rebut / scope-limit / response-only / ask-human
- `Response matrix`: 対応方針、変更先、証拠、status
- `Revision plan`: 実装順序と検証
- `Draft response letter`: editor / reviewer ごとの下書き
- `Files to update`: notes、refs、manuscript、figures
- `Open questions`: 人間判断が必要な論点
- `Validation`: 実行したチェック

## 注意

- reviewer に勝とうとしない。読者が誤解した事実を、原稿が生んだシグナルとして扱う。
- 反論する場合も、まず原稿をより誤解しにくくする余地を探す。
- response letter だけで解決できる問題と、原稿を直すべき問題を混ぜない。
- confidential な reviewer text を web 検索語、Issue、上流 feedback、公開 PR description に入れない。
- AI が response draft に関与した場合は、投稿先ポリシーに応じて `/ai-disclosure-check` で確認する。

## Codex 実行メモ

- `manuscript/mirror/status.md` で source-of-truth を確認する。
- `review/feedback/` や `notes/views/peer-review.md` を更新する場合は raw quote ではなく要約と comment ID を中心にする。
- 追加文献が必要なら `/research-related-work` または `/update-refs` へ渡す。
- 外部 source channel の到達経路が未整理なら `/source-reach-scan` へ渡す。
- reviewer comment が中心主張の assumption を突いている場合は `/scientific-gate` へ戻す。
- 追加解析が必要なら `requests/analysis/` に切り出す。
- 原稿や refs を編集したら `make mirror-check`、`make citation-check`、必要に応じて `make ci` を実行する。
