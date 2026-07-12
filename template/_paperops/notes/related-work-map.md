# 関連研究マップ

Deep research の結果を、そのまま文献レビュー本文へ流し込まず、論文の問い、主張、反論、位置づけへ翻訳するための作業ノート。

広い探索や web search の raw output は `_paperops/refs/research/` に一時保持し、採用する文献だけ `_paperops/refs/summaries/`、`manuscript/shared/bib/references.bib`、必要なら `_paperops/model/research/sources/` と `_paperops/notes/views/claim-evidence-map.md` へ昇格する。

Web、GitHub、動画、RSS、SNS、議論サイトなど複数の外部 source channel を使う場合は、先に `_paperops/notes/source-reach.md` と `/source-reach-scan` で到達経路、credential need、raw capture policy、refs への昇格先を決める。

## 調査スコープ

- 調査トピック: 未記入
- 研究質問との関係: 未記入
- 対象期間: 未記入
- 対象領域・会議・ジャーナル: 未記入
- 除外する文献・領域: 未記入

## Research outline

`_paperops/refs/research/<topic-slug>/outline.toml` に置く調査設計の要約。

| item ID | 調査対象 | 理由 | 優先度 | 状態 |
| --- | --- | --- | --- | --- |
| RW-0001 | 未記入 | 未記入 | high / medium / low | planned / searched / summarized / rejected |

## Field framework

調査対象ごとに集める観点。文献レビューに必要なものだけに絞る。

| field | 目的 | detail level | 本文への使い道 |
| --- | --- | --- | --- |
| 未記入 | 未記入 | brief / moderate / detailed | background / contrast / method / limitation / related-work-only |

## Source clusters

| cluster ID | テーマ | 主要文献 | 論文内の役割 | 不足している証拠 |
| --- | --- | --- | --- | --- |
| CL-0001 | 未記入 | 未記入 | canonical / recent / competing explanation / method reference / negative evidence | 未記入 |

## Debate matrix

関連研究の議論を、単なる列挙ではなく対立軸として整理する。

| debate ID | 論点 | 立場 A | 立場 B | この原稿での扱い |
| --- | --- | --- | --- | --- |
| DB-0001 | 未記入 | 未記入 | 未記入 | 未記入 |

## 採用候補

`_paperops/refs/summaries/` と `.bib` へ昇格する文献だけを書く。

| citation key | 採用理由 | summary path | claim / section | verification status |
| --- | --- | --- | --- | --- |
| 未記入 | 未記入 | `_paperops/refs/summaries/...` | 未記入 | unchecked / metadata-checked / read / cited |

## Source card 昇格ルール

summary だけでよい文献は `_paperops/refs/summaries/` に留める。本文の supported claim や Methods / Discussion の根拠に使う場合は、以下の条件を `promotion_required_when` に記録して source card に昇格する。

| trigger | source card に昇格する理由 | 記録する境界 |
| --- | --- | --- |
| claim_boundary | 主張できる範囲、否定できない範囲、引用元が支える限界を決める | claim / section / unsupported claim |
| parameter_choice | 閾値、比較条件、評価指標、データ選別、実験設定を正当化する | parameter / method unit / alternative |
| reviewer_objection | 想定査読者の反論、代替説明、否定証拠を受ける | objection / response route / required evidence |
| method_precedent | 方法、ベンチマーク、可視化、評価基準の先行例として使う | method dependency / reproducibility note |

## Source reach 由来の finding

| finding ID | source channel | 要約 | 関連する debate / claim | 昇格判断 |
| --- | --- | --- | --- | --- |
| SF-0001 | paper-metadata / github / web-page / video-transcript / rss-news / social-discussion | 未記入 | 未記入 | promote / hold / reject |

## 使わない文献

| source | 使わない理由 | 再確認条件 |
| --- | --- | --- |
| 未記入 | scope 外 / 低品質 / 重複 / 古い / 未検証 | 未記入 |

## 本文に入れる議論

- イントロで使う背景:
- Related Work で比較する系譜:
- Methods で参照する手法:
- Discussion で扱う反論:
- Limitations に回す未解決点:

## 未解決の文献タスク

- 未記入
