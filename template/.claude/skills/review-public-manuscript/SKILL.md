---
name: review-public-manuscript
description: 投稿前原稿を外部読者視点でレビューする。PDF または公開原稿だけを入力に、未定義語・再現性ギャップ・追加解析候補を洗い出す。
argument-hint: "<pdf-or-public-manuscript-path>"
allowed-tools: Read, Glob, Grep, Bash
---

# review-public-manuscript

投稿前原稿を、repo 内部の notes やローカル run 情報を知らない外部読者としてレビューする。

## 入力

- `<pdf-or-public-manuscript-path>`: 投稿前 PDF、または公開原稿として読者に見える TeX/Markdown/テキスト。
- 入力が複数ある場合は、公開される本文・図表・補足資料だけを対象にする。

## 読んではいけないもの

レビューの独立性を保つため、ユーザーが明示しない限り以下は読まない:

- `notes/`
- `refs/local/`
- ローカル run 名、working output、未公開解析ノート
- 原稿に反映されていない内部モデル説明

## 手順

1. 入力アーティファクトが公開読者に見えるものか確認する。足りない場合は、レビュー対象を限定して明記する。
2. 原稿だけから、研究目的、データ、方法、結果、主張を再構成する。
3. 内部文脈なしでは意味が取れない語を抽出する:
   - 未定義の event catalog、quality subset、run label、内部モデル名
   - 図中にだけ出る略語や変数名
   - 本文と図表で表記が揺れている用語
4. 再現性ギャップを列挙する:
   - data product、期間、selection flow、sample size
   - fit 式、モデル式、座標系、統計指標
   - 外部データ、前処理、除外条件、uncertainty
5. 追加解析候補を High / Medium / Low に分類する。
6. 対応を以下に分解する:
   - 原稿修正
   - 図表追加または図注修正
   - methods / data availability 追記
   - 将来課題化

## 独立レビューの扱い

ユーザーが独立 subagent や別文脈レビューを明示的に許可した場合は、公開アーティファクトだけを渡し、repo 文脈を fork しない設定でレビューさせる。許可がない場合は、自分で公開入力だけに注意を限定してレビューする。

## 出力形式

- `Public-reader summary`: 外部読者として理解できた主張を 3-5 点で要約
- `Blocking gaps`: 投稿前に直すべき未定義語・再現性不足
- `Major revisions`: 説明不足や図表不足
- `Minor revisions`: 表記、定義、参照、図注の改善
- `Additional analyses`: High / Medium / Low の追加解析候補
- `Action checklist`: 原稿、図表、methods/data availability、将来課題に分けた対応リスト

## 注意事項

- 内部ノートから補完せず、原稿に書かれていないことは「読者には見えない」と扱う。
- 原稿の科学的主張を強める提案と、単なる文言修正を分ける。
- レビュー結果は厳しめでよいが、投稿前に実行可能な単位へ分解する。
