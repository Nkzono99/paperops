---
name: review-public-manuscript
description: 投稿前原稿を外部読者・一般研究者視点でレビューする。PDF または公開原稿だけを入力に、未定義語・ローカル語・暗黙前提・再現性ギャップを洗い出す。
argument-hint: "<pdf-or-public-manuscript-path> [general-researcher|reader-assumptions|local-terminology]"
allowed-tools: Read, Glob, Grep, Bash
---

# review-public-manuscript

投稿前原稿を、repo 内部の notes やローカル run 情報を知らない外部読者としてレビューする。

通常の scientific review に加えて、一般研究者・隣接分野査読者・再現性重視の読者として、ローカル語、実装語、暗黙前提が公開原稿だけで理解できるかを検査する。

## 入力

- `<pdf-or-public-manuscript-path>`: 投稿前 PDF、または公開原稿として読者に見える TeX/Markdown/テキスト。
- 入力が複数ある場合は、公開される本文・図表・補足資料だけを対象にする。
- `manuscript/mirror/status.md` は source-of-truth 言語の確認に限って読んでよい。ただし、不足説明の補完には使わない。

## ペルソナ / チェックモード

引数やユーザー依頼に以下が含まれる場合は、通常レビューとは別枠で結果を出す:

- `general-researcher`: 著者の codebase を知らない隣接分野研究者として読む。
- `reader-assumptions`: 読者が本文だけから復元できない前提を探す。
- `local-terminology`: run label、directory name、script name、simulator flag、analysis artifact name を探す。
- `public-reproducibility`: data availability、case count、diagnostic assumptions、figure/table label から再現性ギャップを探す。

## 読んではいけないもの

レビューの独立性を保つため、ユーザーが明示しない限り以下は読まない:

- `notes/`
- `refs/local/`
- ローカル run 名、working output、未公開解析ノート
- 原稿に反映されていない内部モデル説明
- private run inventory や filesystem 上の解析 artifact

## 手順

1. 入力アーティファクトが公開読者に見えるものか確認する。足りない場合は、レビュー対象を限定して明記する。
2. 原稿だけから、研究目的、データ、方法、結果、主張を再構成する。
3. 内部文脈なしでは意味が取れない語を抽出する:
   - 未定義の event catalog、quality subset、run label、内部モデル名
   - campaign-internal label（例: `Series A/B/C`）や project-local naming
   - simulator-specific flag、namelist key、code option
   - filesystem 名、script 名、HDF5 等の artifact 名が scientific category と混ざっている箇所
   - 図中にだけ出る略語や変数名
   - 本文と図表で表記が揺れている用語
4. ローカル語を公開語に置き換える候補を作る:
   - local label から physical condition name へ
   - code flag から physical boundary condition へ
   - artifact name から public data product / diagnostic へ
   - run inventory から selection criterion / calibration subset へ
5. 再現性ギャップを列挙する:
   - data product、期間、selection flow、sample size
   - case count、measurement count、levels / bins / points の内訳
   - fit 式、モデル式、座標系、統計指標
   - 外部データ、前処理、除外条件、uncertainty
   - time averaging、final frame、smoothing / interpolation、units / normalization
   - figure titles、legends、axis labels、table headers に残る internal labels
6. 追加解析候補を High / Medium / Low に分類する。
7. 対応を以下に分解する:
   - 原稿修正
   - 図表追加または図注修正
   - methods / data availability 追記
   - 将来課題化

## 独立レビューの扱い

ユーザーが独立 subagent や別文脈レビューを明示的に許可した場合は、公開アーティファクトだけを渡し、repo 文脈を fork しない設定でレビューさせる。許可がない場合は、自分で公開入力だけに注意を限定してレビューする。

Codex で subagent を使う場合、main agent は repo-aware editor として修正方針を統合し、subagent は `fork_context=false` 相当で一般研究者 reviewer として読む。subagent には `notes/`、private refs、run output を渡さない。

## 出力形式

- `Public-reader summary`: 外部読者として理解できた主張を 3-5 点で要約
- `Blocking gaps`: 投稿前に直すべき未定義語・再現性不足
- `Reader-assumption gaps`: 公開原稿だけでは復元できない前提
- `Local terminology`: local label / simulator term / artifact term と推奨 public term の表
- `Major revisions`: 説明不足や図表不足
- `Minor revisions`: 表記、定義、参照、図注の改善
- `Figure/table cleanup`: title、legend、axis、caption、table header の置換候補
- `Data availability additions`: 公開データ、選別基準、diagnostic の追記候補
- `Additional analyses`: High / Medium / Low の追加解析候補
- `Rewrite patch plan`: file / block ID 単位の修正計画
- `Action checklist`: 原稿、図表、methods/data availability、将来課題に分けた対応リスト

## 注意事項

- 内部ノートから補完せず、原稿に書かれていないことは「読者には見えない」と扱う。
- 原稿の科学的主張を強める提案と、単なる文言修正を分ける。
- レビュー結果は厳しめでよいが、投稿前に実行可能な単位へ分解する。
- 科学的判断そのものを置き換えず、読者に必要な前提、語彙、選別基準を指摘する。
- 原稿修正に進む場合は `manuscript/ja/` の source-of-truth と `% block: ...` ID を尊重し、EN mirror は `sync-ja-en` の方針で同期する。
