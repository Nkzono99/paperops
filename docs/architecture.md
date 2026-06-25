# アーキテクチャ

`paperops` は、テンプレート保守と個別論文執筆を分ける。目的は、AI に原稿を直接書かせることではなく、研究状態を検証可能な中間層へ整理し、承認済みの材料だけを論文本文へ変換することである。

## ルート層

リポジトリルートは、下流論文リポジトリへ配るものを管理する。

- `template/`: bundled scaffold の source of truth
- `src/paperops/`: `pops` CLI
- `.github/workflows/`: reusable workflow
- `.github/ISSUE_TEMPLATE/`: テンプレート改善の受け口
- `.agents/skills/`, `.claude/skills/`: テンプレート保守 skill
- `docs/`, `CHANGELOG.md`: 変更方針と配布記録

この層の役割は、ハーネスを安全に進化させることである。

## 下流論文層

`template/` は個別論文リポジトリに展開される。主な層は次の通り。

- `manuscript/`: 日英原稿、ミラー制御、投稿先情報
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX
- `contracts/`: Introduction / Methods / Results / Discussion / Conclusion の入出力契約
- `refs/`: 文献サマリー、関連研究調査、外部 source、外部 project link、外部 bundle import state
- `_handoff/`: 人間から AI へ渡す未整理ファイル
- `_archives/`: 過去稿を sealed split bundle として封印する scratch archive
- `evidence/`: result / figure / source card
- `claims/`: claim / scientific gate / argument card
- `review/`: feedback / review round / response card
- `requests/`: analysis / writing request card
- `notes/`: project brief、読者モデル、AI 利用、再現性、`notes/views/`

`evidence/`、`claims/`、`review/`、`requests/` がカード正本である。`notes/views/` は正本を人間と Agent が読むための view だが、すべてを単なる派生 cache として扱わない。

## 層契約

| 層 | 役割 | 正本性 | 主な更新入口 |
| --- | --- | --- | --- |
| `evidence/` | result / figure / source を論文上の証拠単位へ整理する | 正本 | `/map-result-patterns`, `/research-related-work` |
| `claims/` | claim、scientific gate、argument を管理する | 正本 | `/scientific-gate`, `/design-manuscript-claims` |
| `review/` | 人間レビュー、模擬査読、実査読 response を管理する | 正本 | `/integrate-writing-feedback`, `/peer-review-manuscript`, `/respond-to-peer-review` |
| `requests/` | 追加解析や改稿依頼を管理する | 正本 | `/integrate-writing-feedback`, runops handoff |
| `notes/views/` の pure overview view | 正本カードを俯瞰する | 派生 view | 該当 card 更新後に手動または半自動で更新 |
| `notes/views/` の controlled authoring view | 本文での呼び方、条件名、概念語、読者向け語彙を統制する | 編集可能な統制 view | `/public-terminology-pass`, `/contextualize-conditions`, `/polish-ai-draft` |
| `paper_ir` | card / view から Writer に渡す材料を section ごとにまとめる | 生成一時物 | `finish-manuscript` の section compiler phase |
| `contracts/` | section ごとの読者質問、入力、出力、禁止構造を定める | 既定契約 | `finish-manuscript` の plan-section / audit-section |
| `manuscript/writing-profile.yml` | 論文種別、投稿先、分野別要求を section 契約へ重ねる | プロジェクト設定 | 初期 setup、投稿先変更時 |
| `.paperops/cache/` | section plan や一時 IR を置く | Git 管理しない生成物 | `finish-manuscript` の plan-section |
| `manuscript/` | 読者へ出す本文 | 成果物 | Writer / editor pass |
| `submission/` | 投稿先に合わせた提出版 | 派生成果物 | `prepare-submission` 相当の投稿前作業 |
| `_handoff/` | 未整理入力の一時置き場 | Git 管理しない | 人間入力、raw file intake |
| `_archives/` | sealed scratch archive | 通常読まない封印物 | `pops scratch archive/restore` |

`notes/views/concept-terms.md` と `notes/views/condition-context-map.md` は controlled authoring view として扱う。ここには「カード正本から見える意味」を本文語彙へ変換するときの判断を書く。

## 情報フロー

1. 人間は主に原稿レビュー、自然文の指示、判断を出す。
2. Agent は必要に応じて feedback / evidence / claim / request card を更新する。
3. Abstract、Conclusion、主要図表に使う claim は `claims/gates/` で readiness を確認する。
4. 本文に出る強い名詞句は `notes/views/concept-terms.md` で確認し、accepted term、普通の文へほどく語、avoid 語を分ける。
5. `contracts/<section>.yml` と `manuscript/writing-profile.yml` を重ねて、section が答える読者質問と必要出力を確認する。
6. 原稿を書く前に、必要な範囲で `paper_ir` と section plan を作る。生成物は `.paperops/cache/` に置き、Git 管理しない。
7. section compiler が Methods / Results / Discussion それぞれの reader question、answer、evidence、figure、caveat location、sentence budget を決める。
8. Writer は `paper_ir` と承認済み claim package を使って本文を書く。Writer に生の card ontology を直接渡しすぎない。
9. 原稿修正は最後に行う。本文だけ直して上流の claim や evidence を放置しない。
10. 外部 project や runops の成果物は `refs/links.toml`、`refs/local/locations.toml`、`refs/imports/` で link、実パス、import state を分ける。
11. 1から書き直す評価では、`pops scratch archive` で現行層を `_archives/` に封印し、`pops scratch reset` で作業層だけを初期化する。通常の Agent workflow は `_archives/` を読まない。

## paper_ir と section compiler

`paper_ir` は、既存 card と controlled view から作る生成一時物である。新しい手書き正本にはしない。目的は、研究 integrity 層と文章層の間に、読者向けの変換契約を置くことである。

`contracts/` は文章テンプレートではなく、section ごとの入出力契約である。Introduction は `problem -> unresolved tension -> precise gap -> approach -> contribution -> scope` のような論理機能を持ち、Methods / Results / Discussion はそれぞれ情報配置、subsection 契約、推論型を明示する。`manuscript/writing-profile.yml` は `paper_type: computational_modeling` のような論文種別 overlay と投稿先要求を重ねる。`finish-manuscript` は `plan-section -> draft-section -> audit-section` の順で使い、plan は必要なら `.paperops/cache/section-plan-<section>.yml` に置く。

`paper_ir` の最小単位は次を持つ。

- `id`
- `section`
- `reader_question`
- `answer`
- `evidence`
- `warrant`
- `role`
- `preceded_by`
- `followed_by`
- `caveat_location`
- `sentence_budget`
- `forbidden_terms`
- `plain_language_terms`

section compiler は、`finish-manuscript` の中で Writer の前に走る段階として扱う。

- `compile-methods`: method unit ごとに、本文 / supplement / code への配分、非標準性、結果感度、再実装に必要な情報を決める。
- `compile-results`: reader question -> one-sentence answer -> quantitative evidence -> figure -> consequence の順に、結果の読み順を作る。
- `compile-discussion`: observation / inference / mechanism_hypothesis / alternative_explanation / implication / prediction / limitation を分ける。

これにより、AI が持っている情報を均等に説明したり、内部 label を本文へ漏らしたり、limitation だけを過剰に複製したりする失敗を減らす。

## 設計原則

- 下流作成は `pops init` に統一する。
- `pops update-paperops` はハーネス管理ファイルだけを更新し、下流固有の原稿・notes・refs・カードを自動上書きしない。
- 作業用ドキュメントは原則日本語で書く。識別子、citation key、TOML field name は英語のままでよい。
- raw PDF、未整理ファイル、個人環境の絶対パス、confidential correspondence は tracked な共有ファイルへ混ぜない。
- `paper_ir` や session context のような生成一時物は、明示的な starter artifact でない限り Git 管理しない。
- 検証は strict / advisory / diagnostic を分ける。管理のための checklist を、文章生成の generator として使いすぎない。
