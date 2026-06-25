---
name: review-public-manuscript
description: Use when reviewing public manuscript text for reader assumptions and reproducibility gaps.
---

# review-public-manuscript

節単位・週次・投稿前の公開原稿を、repo 内部の notes やローカル run 情報を知らない外部読者としてレビューする。

通常の scientific review に加えて、一般研究者・隣接分野査読者・再現性重視の読者として、ローカル語、実装語、暗黙前提が公開原稿だけで理解できるかを検査する。

投稿前 review では editorial architect として、storyline、Results hierarchy、Discussion functions、section-depth を明示的に見る。Results が図表列挙、Discussion が limitation 列挙だけなら、Submission hygiene より先の blocking gap として返す。

ユーザーが reviewer 2、major/minor comments、accept/reject recommendation、meta-review のような査読票形式を求めている場合は `/peer-review-manuscript` を使う。実際に返ってきた査読コメントへの返答案や revision plan が目的なら `/respond-to-peer-review` を使う。

## 入力

- `<pdf-or-public-manuscript-path>`: 投稿前 PDF、または公開原稿として読者に見える TeX/Markdown/テキスト。
- 入力が複数ある場合は、公開される本文・図表・補足資料だけを対象にする。
- `manuscript/mirror/status.md` は source-of-truth 言語の確認に限って読んでよい。ただし、不足説明の補完には使わない。

## 発動タイミング

- `section`: 1 節を書いた直後に、その節と関連する figure/table caption だけを読む。修正コストが小さいうちに未定義語、主張の飛躍、読者前提を拾う。
- `weekly`: 週 1 回、Abstract、Introduction、title candidates、figure/table captions だけを読む。中心主張、公開語彙、図表 story が読者に通るかを確認する。
- `pre-submit`: 投稿前に PDF または投稿対象 TeX 全体を読む。Data/code availability、AI disclosure、reproducibility、local terminology、submission-specific formatting の詰まりを重点確認する。

タイミング指定がない場合は、入力の粒度から最も近いモードを推定し、出力の冒頭で「今回は section / weekly / pre-submit のどれとして読んだか」を明記する。

## ペルソナ / チェックモード

引数やユーザー依頼に以下が含まれる場合は、通常レビューとは別枠で結果を出す:

- `general-researcher`: 著者の codebase を知らない隣接分野研究者として読む。
- `reader-assumptions`: 読者が本文だけから復元できない前提を探す。
- `local-terminology`: run label、directory name、script name、simulator flag、analysis artifact name を探す。
- `condition-context`: `2/12`、`0/8`、case、condition、series などの denominator が読者に意味を持つ文脈へ翻訳されているかを探す。
- `public-reproducibility`: data availability、case count、diagnostic assumptions、figure/table label から再現性ギャップを探す。
- `editorial-architect`: storyline、Results hierarchy、Discussion functions、section-depth を探す。

## 読んではいけないもの

レビューの独立性を保つため、ユーザーが明示しない限り以下は読まない:

- `notes/`
- `refs/local/`
- ローカル run 名、working output、未公開解析ノート
- 原稿に反映されていない内部モデル説明
- private run inventory や filesystem 上の解析 artifact

## 手順

1. 入力アーティファクトが公開読者に見えるものか確認し、section / weekly / pre-submit のレビュー粒度を明記する。足りない場合は、レビュー対象を限定して明記する。
2. 原稿だけから、研究目的、データ、方法、結果、主張を再構成する。weekly では Abstract + Introduction + captions から中心主張と figure story を再構成する。
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
6. editorial architect として、Results hierarchy と Discussion functions を確認する:
   - Results の各 subsection が reader question、answer、quantity、figure/table、consequence を持つか
   - Discussion が mechanism_warrant、prior_work_delta、alternative_or_boundary、implication、decisive_next_test を持つか
   - storyline が title / abstract / conclusion で保存されているか
   - `section_depth` の floor を、JA は TeX noise を除いた `ja_chars`、EN は TeX noise を除いた `en_words` として確認しているか
   - section-depth 不足を Submission hygiene と混同していないか
   - one-paragraph subsections が、必要な読者質問に答える単位ではなく過剰分割になっていないか
7. 追加解析候補を High / Medium / Low に分類する。
8. 対応を以下に分解する:
   - 原稿修正
   - 図表追加または図注修正
   - methods / data availability 追記
   - 将来課題化

## 独立レビューの扱い

ユーザーが独立 subagent や別文脈レビューを明示的に許可した場合は、公開アーティファクトだけを渡し、repo 文脈を fork しない設定でレビューさせる。許可がない場合は、自分で公開入力だけに注意を限定してレビューする。

Codex で subagent を使う場合、main agent は repo-aware editor として修正方針を統合し、subagent は `fork_context=false` 相当で一般研究者 reviewer として読む。subagent には `notes/`、private refs、run output を渡さない。

repo-aware editor と public-only reviewer を同じ判断に混ぜない。public-only reviewer は読者が詰まる箇所を検出する役割に留め、修正実装や内部台帳への反映は repo-aware editor が行う。

## 出力形式

- `Public-reader summary`: 外部読者として理解できた主張を 3-5 点で要約
- `Review mode`: section / weekly / pre-submit のどれで読んだか
- `Blocking gaps`: 投稿前に直すべき未定義語・再現性不足
- `Reader-assumption gaps`: 公開原稿だけでは復元できない前提
- `Local terminology`: local label / simulator term / artifact term と推奨 public term の表
- `Count-led claims`: 条件数や case count が主語になっている箇所
- `Missing paper context`: denominator の意味や claim role が本文だけでは分からない箇所
- `Major revisions`: 説明不足や図表不足
- `Minor revisions`: 表記、定義、参照、図注の改善
- `Figure/table cleanup`: title、legend、axis、caption、table header の置換候補
- `Data availability additions`: 公開データ、選別基準、diagnostic の追記候補
- `Storyline / editorial architect`: Results hierarchy、Discussion functions、section-depth の不足
- `Additional analyses`: High / Medium / Low の追加解析候補
- `Rewrite patch plan`: file / block ID 単位の修正計画
- `Action checklist`: 原稿、図表、methods/data availability、将来課題に分けた対応リスト

## 注意事項

- 内部ノートから補完せず、原稿に書かれていないことは「読者には見えない」と扱う。
- 原稿の科学的主張を強める提案と、単なる文言修正を分ける。
- レビュー結果は厳しめでよいが、投稿前に実行可能な単位へ分解する。
- 原稿内容の blocker が残る場合、author metadata、license、Open Research DOI などの Submission hygiene を主 blocker として前面化しない。
- 科学的判断そのものを置き換えず、読者に必要な前提、語彙、選別基準を指摘する。
- 原稿修正に進む場合は `manuscript/ja/` の source-of-truth と `% block: ...` ID を尊重し、EN mirror は `sync-ja-en` の方針で同期する。

## Codex 実行メモ

- PDF または公開原稿だけをレビュー入力とし、`notes/`、`refs/local/`、working output は読まない。
- 1 節を書いた直後は `section`、週次では Abstract + Introduction + title candidates + figure/table captions の `weekly`、投稿前は PDF/投稿対象 TeX 全体の `pre-submit` として扱う。
- モード指定がない場合は入力粒度から推定し、出力冒頭で `Review mode` を明記する。
- ユーザーが独立 subagent を明示的に許可した場合だけ、公開アーティファクトのみを渡して別文脈レビューを依頼する。
- `general-researcher`、`reader-assumptions`、`local-terminology`、`public-reproducibility` の観点を明示された場合は、通常の scientific review と別枠で出力する。
- run label、directory name、simulator flag、analysis artifact name、figure label が公開読者に通じる physical condition / public data product として説明されているか確認する。
- runops project、publication export bundle、raw run directory、campaign、case、production run、smoke/feasibility check は、公開原稿では原則として内部 provenance 語として指摘する。
- 未定義語、ローカル語、暗黙前提、再現性ギャップ、図表 cleanup、Data availability 追記、rewrite patch plan、対応チェックリストに分けて返す。
- repo-aware editor と public-only reviewer を混ぜず、public-only review は読者が詰まる箇所の検出に限定する。修正実装や内部台帳反映は通常の repo 文脈で行う。
