---
name: design-manuscript-claims
description: 原稿を作業報告型から主張中心の論文構造へ再設計する。主張、証拠、補助解析、対照、限界の階層を整理し、必要時のみ rewrite plan を作る。
argument-hint: "[section-or-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# design-manuscript-claims

原稿全体または指定範囲を、実施項目の網羅ではなく、読者に伝えるべき主張を中心に再設計する。

`review-public-manuscript` は公開原稿だけを外部読者として読むレビューである。この skill は repo 内の brief、claim-evidence map、reviewer model、mirror status、JA source of truth も読み、論文の主張階層と rewrite plan を設計する。

## 入力

- `manuscript/mirror/status.md`
- `notes/project-brief.md`
- `notes/contribution-claims.md`
- `notes/claim-evidence-map.md`
- `notes/reviewer-model.md`
- `manuscript/ja/sections/*.tex`（原則として source of truth）
- 必要に応じて `manuscript/en/sections/*.tex`
- figure captions、section headings、abstract、conclusion
- 引数がある場合は、その section、block ID、または scope を優先する

## ゴール

- Core claim を 1 文に圧縮する。
- Essential results を 3-5 項目に絞る。
- 主張、必須証拠、補助証拠、対照、限界、将来課題を分ける。
- 本文に残すもの、Supplement/Appendix に逃がすもの、notes に provenance だけ残すもの、削るものを判断する。
- ユーザーが明示した場合だけ、JA source of truth の rewrite に進む。

## 手順

### 1. 先に骨格を読む

本文を細部から読まず、先に以下を読む:

1. abstract
2. introduction の problem / gap / contribution
3. conclusion
4. section headings
5. figure captions
6. `notes/contribution-claims.md`
7. `notes/claim-evidence-map.md`
8. `notes/reviewer-model.md`
9. `manuscript/mirror/status.md`

この段階で、原稿が読者に約束している主張を仮説として書き出す。

### 2. 作業報告 smell を検出する

以下を優先して探す:

- run 数、解析手順、補助係数が主張と同じ重みで並ぶ
- Results が「実施した全項目の inventory」になっている
- Modeling / Discussion が主張を支える整理ではなく、追加結果の置き場になっている
- 対照実験や sensitivity check が新しい主張のように読める
- caveat や限界が主結果より前に来て読者の負荷になる
- conclusion が claim inventory ではなく run inventory になっている
- figure captions が「何を示す図か」ではなく「何を計算したか」だけを述べる

### 3. 主張と証拠を棚卸しする

各候補主張について、以下の表を作る:

| Claim | Essential evidence | Supporting evidence | Controls | Limits | Current blocks |
|-------|--------------------|---------------------|----------|--------|----------------|

`Current blocks` には `% block: ...` ID または section file を入れる。block ID がない範囲は section と近い見出しで示す。
設計後、ユーザーが了承した claim / evidence / scope / limitation は `notes/claim-evidence-map.md` に反映する。

### 4. 本文の配置を決める

各材料を次に分類する:

- Keep in main text: Core claim を読むために必要
- Compress in main text: 本文には必要だが、短くできる
- Move to supplement/appendix: 再現性や検証には必要だが、主張の読み筋を止める
- Keep in notes/provenance: 執筆判断や解析履歴としては重要だが、公開本文には不要
- Cut: 重複または主張に寄与しない

詳細を本文から削る場合も、必要なら `notes/decision-log.md` や supplement 候補として provenance を残す提案をする。

### 5. claim-centered outline を提案する

新しい outline は、実施順ではなく読者が主張を理解する順に並べる:

1. 問題設定と claim の約束
2. 主要結果
3. 主要結果を説明する mechanism / model
4. 対照と robustness
5. 限界と適用範囲
6. claim inventory としての conclusion

投稿先や分野の慣習を固定しない。原稿固有の科学的判断は、ユーザーに確認すべき仮説として書く。

### 6. rewrite は明示依頼がある場合のみ行う

ユーザーが rewrite を求めた場合だけ、次の順で進める:

1. `manuscript/ja/` を source of truth として編集する。
2. `% block: ...` ID は保持する。削除が必要な場合は、削除理由と移動先を先に示す。
3. 大きな構造変更は block ID 単位の rewrite plan を出してから実施する。
4. EN mirror は直接全面上書きせず、`sync-ja-en` の方針に従って同期する。
5. 最後に `make mirror-check`、必要に応じて `make ci` を実行する。

## 出力形式

- `Core claim`: 1 文
- `Essential results`: 3-5 項目
- `Claim evidence map`: Claim / Essential evidence / Supporting evidence / Controls / Limits / Current blocks
- `Work-report smells`: 読み筋を弱めている箇所
- `Keep / compress / move / cut`: 本文配置の判断
- `Proposed section structure`: 新しい章立て
- `Risks of over-claiming`: 強く言いすぎる危険
- `Rewrite plan by block ID`: rewrite する場合の単位と順序

## 注意事項

- 主張を増やすのではなく、主張の数を減らして階層を見えるようにする。
- 補助解析や対照実験は、主張を支える役割として配置する。
- 科学的判断を template に固定しない。分野固有の判断はユーザーに確認する。
- ミラー整合性を壊さない。JA source of truth と block ID を尊重する。
