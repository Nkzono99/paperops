---
name: research-related-work
description: Use when collecting related work, comparison papers, objections, and summaries.
---

# research-related-work

関連研究を「検索結果の山」ではなく、論文の問い、主張、反論、位置づけへ変換するために使う。

Deep-Research-skills の outline -> field framework -> item deep research -> report という型を参考にするが、paperops では raw findings を正本にしない。正本は `_paperops/refs/summaries/`、`.bib`、`_paperops/notes/related-work-map.md`、必要なら `_paperops/notes/views/claim-evidence-map.md` である。

## 最初に読むファイル

- `_paperops/notes/project-brief.md`
- `_paperops/notes/contribution-claims.md`
- `_paperops/notes/source-reach.md`
- `_paperops/notes/related-work-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/argument-map.md`
- `_paperops/refs/index.md`
- `_paperops/refs/source-reach/README.md`
- `_paperops/refs/summaries/`
- `manuscript/venue.md`

## 手順

### 1. 調査スコープを固定する

まず `_paperops/notes/related-work-map.md` の `調査スコープ` を更新する。

- 調査トピック
- 研究質問との関係
- 対象期間
- 対象領域・会議・ジャーナル
- 除外する文献・領域

不明な場合は、1 問だけ確認する。ユーザーが「適当に進めて」と言った場合は、原稿の中心主張と投稿先読者から保守的に決める。

### 2. Research outline を作る

`_paperops/refs/research/<topic-slug>/outline.toml` を作るか更新する。既存の outline がある場合は追記する。

推奨フィールド:

```toml
topic = "short topic"
time_range = "unlimited / since YYYY / last N years"
status = "planned"

[[items]]
id = "RW-0001"
name = "paper, method, benchmark, research thread, or debate"
why = "why this item matters"
priority = "high"
status = "planned"
```

調査対象は文献名だけに限らない。手法、ベンチマーク、研究コミュニティ、反論軸、近年の潮流も item にしてよい。

### 3. Field framework を作る

`_paperops/refs/research/<topic-slug>/fields.toml` に、item ごとに集める観点を置く。

推奨フィールド:

```toml
[[fields]]
name = "core_claim"
description = "その文献・研究軸が何を主張しているか"
detail_level = "moderate"
use_in_manuscript = "background / contrast / method / limitation / related-work-only"
```

field は増やしすぎない。文献レビュー本文、claim scope、反論処理に使わない field は raw report 側に留める。

### 4. 深掘り調査を行う

各 item について、一次情報を優先して調べる。

- 論文ページ、DOI、arXiv、出版社ページ
- 公式 code / dataset / benchmark
- 著者ページ
- survey paper や citation graph
- 必要な場合のみ blog / GitHub / discussion

web 検索が必要な場合、未公開原稿や private note の文面をそのまま検索語にしない。検索には公開可能な概念語だけを使う。

GitHub、動画、RSS、SNS、議論サイト、platform-specific source を複数使う場合は、先に `/source-reach-scan` で channel、preferred route、fallback、credential need、raw capture policy を決める。raw output を直接文献レビューに入れず、`_paperops/notes/source-reach.md` または `_paperops/refs/source-reach/` で到達経路と確認状態を分ける。

raw findings は `_paperops/refs/research/<topic-slug>/results/` に一時保存してよいが、既定では Git 管理しない。

### 5. 議論へ統合する

調査結果を `_paperops/notes/related-work-map.md` に移す。

- `Source clusters`: canonical、recent、competing explanation、method reference、negative evidence に分ける。
- `Debate matrix`: 立場 A / B と、この論文でどう扱うかを書く。
- `採用候補`: `.bib` と `_paperops/refs/summaries/` へ昇格する文献だけを書く。
- `使わない文献`: scope 外、低品質、古い、重複、未検証を残す。

この時点では本文を書き換えない。ユーザーが本文化を求めたら `/design-manuscript-claims`、`/paragraph-surgery`、`/sync-ja-en` へ渡す。

### 6. refs へ昇格する

採用する文献だけ、次を更新する。

- `manuscript/shared/bib/references.bib`
- `_paperops/refs/summaries/<citation-key>.md`
- 必要なら `_paperops/refs/index.md`
- claim を支える場合は `_paperops/notes/views/claim-evidence-map.md`

文献の存在、年、著者、DOI、主張内容を確認できない場合は `unchecked` または `unverified` と明示し、supported claim の証拠にしない。

### 7. source card への昇格を判定する

`_paperops/refs/summaries/` は採用文献の要約であり、すべてを source card にしない。背景、分野整理、関連研究の列挙だけなら summary の `promotion_decision: hold` に留める。

次のいずれかに該当する場合は `_paperops/model/research/sources/` の source card に昇格し、`promotion_required_when` と理由を記録する。

- `claim_boundary`: 本稿の claim scope、支えられない主張、比較範囲を決める。
- `parameter_choice`: Methods のパラメータ、閾値、比較条件、評価指標、データ選別を正当化する。
- `reviewer_objection`: 想定査読者の反論、代替説明、否定証拠、limitation response に使う。
- `method_precedent`: 方法、ベンチマーク、可視化、再現性情報の先行例として使う。

昇格した source card は claim / manuscript block / verification state を持つ。昇格しない summary を supported claim の直接根拠にしない。

## 出力

- `Research outline`: 追加・更新した item と field
- `Search plan`: 優先ソース、検索語、対象期間
- `Source clusters`: 関連研究の束
- `Debate matrix`: 対立軸とこの論文での扱い
- `Promotion list`: `_paperops/refs/summaries/` と `.bib` に昇格する文献
- `Source card decisions`: hold / source-card / reject と、claim_boundary / parameter_choice / reviewer_objection / method_precedent の該当
- `Do not use`: 使わない文献と理由
- `Next actions`: 読む、要約する、引用する、保留する、捨てる
- `Files updated`: 更新した notes / refs / bib
- `Checks run`: 実行した lint / citation / link checks

## 注意

- raw search result は文献レビューではない。
- 直接引用は必要最小限にし、長い抜粋を tracked ファイルに残さない。
- 関連研究の議論は日本語で書く。citation key、DOI、title、field name は英語のままでよい。
- 既存 source の DOI、metadata、投稿日、投稿先 policy、外部 repository の軽い確認は必要に応じて web で行い、出典リンクを残す。新規 source channel、credential、raw capture、SNS / 動画 / platform-specific source が絡む場合は先に `/source-reach-scan` へ戻す。
- 採用判断がまだなら `_paperops/notes/related-work-map.md` に留め、`claim-evidence-map.md` の supported claim へ昇格しない。
- 外部 source channel の到達経路や raw capture 方針は `_paperops/notes/source-reach.md` に残し、採用した finding だけを `_paperops/refs/summaries/` や `.bib` へ昇格する。

## Codex 実行メモ

- ユーザーが明示しない限り、`manuscript/` は編集しない。
- `_paperops/refs/research/**/results/` と `report.generated.md` は一時成果物として扱う。
- bib を編集したら `/update-refs` または `make lint-bib` / `make citation-check` で確認する。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
