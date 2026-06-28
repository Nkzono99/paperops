---
name: audit-ai-draft
description: AI が作った論文初稿を、列挙的な作業報告から主張中心の原稿へ戻すために診断し、論旨設計メモと改稿計画を作る。
---

# audit-ai-draft

AI に一旦書かせた原稿、または大きく自動生成した節を、投稿可能な論文の構成へ近づけるために使う。公開読者としての読みに加え、repo 内の `_paperops/notes/` と `_paperops/refs/` を見て、何を主張として前面に出し、何を根拠・境界条件・補助情報へ下げるかを設計する。

ユーザーが「まず俯瞰的に」「まだ直さず違和感を出して」「meta 的に発想を広げたい」と頼んでいる場合は、この skill で診断へ固定する前に `/open-paper-scan` を使う。

## 入力

- PDF、TeX、または対象 section / block ID
- `_paperops/notes/project-brief.md`
- `_paperops/notes/views/scientific-gate.md`
- `_paperops/notes/related-work-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/argument-map.md`
- `_paperops/notes/views/concept-terms.md`
- `_paperops/notes/reviewer-model.md`
- `_paperops/notes/ai-draft-polish.md`
- `_paperops/notes/reproducibility.md`
- `manuscript/mirror/terminology.yml`
- 必要に応じて `_paperops/refs/links.toml` と `_paperops/refs/summaries/`

`_archives/` は読まない。過去稿との比較は、ユーザーが明示的に archive compare / restore を頼んだ場合だけ行う。

## 目的

- 節ごとに一つずつ言及するだけの均等な構成を避け、中心主張、機構、証拠、境界条件の階層を作る。
- `design-paper-storyline` の editorial architect 視点で、storyline、Results hierarchy、Discussion functions、section-depth の不足を本文 polish より先に検出する。
- `12 条件中 2 条件`、`8 条件中 0 条件`、保存時刻数、run 数のようなローカル結果を、そのまま本文の主張にせず、論文内での意味へ抽象化する。
- `これは直接証明ではない`、`主張しない`、`screening である` のような防御的記述を、必要な場所へ集約する。
- 内部 provenance 語、local run label、directory name、artifact name を公開語へ置換する。
- AI Writer が「この claim を強めるための追加作業」「後で埋める」「authoring note」のような執筆意図を本文 prose に混ぜていないか確認し、`% INTENT:` / `% TODO-PAPER:`、`_paperops/notes/`、`_paperops/requests/` へ戻す。
- データがまだ無いことを一般的な Future Work や defensive caveat に畳んでいないか確認する。投稿前に現実的な追加シミュレーションで閉じられ、期待結果の根拠がある場合は `draft-predicted-results` へ戻し、`% PREDICTED-RESULT:` / `% SIM-REQUEST:` と `_paperops/requests/analysis/` を接続する。
- `surface-element charge update` や `code/reproducibility package` のような concept-term compression を検出し、claim / argument / evidence card の意味を本文語彙へ圧縮しすぎていないか判断する。
- `_paperops/notes/views/argument-map.md` と `_paperops/notes/views/claim-evidence-map.md` を更新する改稿計画を出す。
- 関連研究の位置づけが未整理な場合は、本文を磨く前に `_paperops/notes/related-work-map.md` または `/research-related-work` へ戻す。
- 中心主張や Abstract / Conclusion に入る claim が `scientific-gate` で未承認なら、文体修正ではなく `/scientific-gate` へ戻す。
- AI らしい定型文だけが問題で claim / evidence / gate は固定済みの場合は、本文診断後に `/polish-ai-draft` へ渡す。

## 手順

### 1. Public-only first read

最初に公開原稿だけを読み、repo 内部知識で補完しない。以下を短く書く:

- 読者が理解できる中心主張
- 読者が迷う主張
- 節構成が列挙型に見える箇所
- storyline が未固定で、Results hierarchy や Discussion functions が薄い箇所
- 面白い結果なのに埋もれている箇所
- 防御的記述が主張を弱めている箇所

### 2. Local-detail smell を検出する

以下の表現を探す:

- `N 条件中 M 条件`、`N/M`、`N 個の保存時刻のうち M 個`
- `screening`、`exploratory`、`bracket`、`caveat` が結果の主語になっている箇所
- `主張しない`、`証明ではない`、`限定される` が各節で繰り返される箇所
- run label、export 名、directory 名、script 名、artifact 名
- `claim を強めるための追加作業`、`後で埋める`、`TODO`、`authoring note` など AI 執筆時の meta instruction が本文 prose に出ている箇所
- 未実行の追加シミュレーションを Future Work や limitation として弱く片付け、投稿前に実行する選択肢を消している箇所
- 図の caption が「何を示すか」ではなく「何を計算したか」だけを述べる箇所
- hyphen / slash compound や 3 語前後の強い英語名詞句が一文に集中する箇所。必要なら `_paperops/notes/views/concept-terms.md` に記録し、accepted、plain-language、avoid を分ける。

### 3. Local-to-claim abstraction を作る

本文に散らばる結果列挙は、claim に直接変換せず、先に `_paperops/notes/views/result-pattern-map.md` の result pattern / evidence packet へ戻す。観察された contrast、effect direction / magnitude、negative or null cases、uncertainty / failure mode、candidate interpretation を整理してから、claim role を判断する。

ローカルな数え上げを、以下のいずれかへ分類する:

- **Core evidence**: 中心主張を直接支える。本文で強く扱う。
- **Mechanism evidence**: なぜそうなるかを説明する。因果・機構の節へ置く。
- **Boundary condition**: 主張が破れる条件。Discussion か negative control として扱う。
- **Screening / provenance**: 本文では圧縮し、`_paperops/notes/reproducibility.md`、supplement、figure-data package へ退避する。
- **Discard / future work**: 今の主張に寄与しない。

`_paperops/notes/views/result-pattern-map.md` と `_paperops/notes/views/argument-map.md` の「ローカル条件から公開主張への抽象化」を埋める。

### 4. Defense budget を決める

同じ caveat を何度も繰り返さない。重要な caveat は、Abstract / Methods / Discussion / Data Availability のどこか一箇所で強く明示し、Results では主張と証拠を前に出す。

`_paperops/notes/views/argument-map.md` の「Defense budget」を埋める。

### 5. 改稿計画を作る

ユーザーが明示的に本文編集を求めるまでは、原稿を直接書き換えない。まず以下を出す:

- 一文の中心主張
- story spine / storyline
- Section-level reorder / compression plan
- Results hierarchy
- Discussion functions
- Figure story
- Keep / compress / move / cut
- block ID 単位の rewrite plan
- `_paperops/notes/views/claim-evidence-map.md` と `_paperops/notes/views/argument-map.md` の更新案
- 関連研究・反論文献の整理が必要なら `_paperops/notes/related-work-map.md` の更新案
- scientific gate で止めるべき claim と、polish だけで直してよい段落

Results が図表や条件の列挙に見える、または Discussion が limitation の列挙だけに見える場合は、`paragraph-surgery` や Submission hygiene へ進まず `design-paper-storyline` へ戻す。これは section-depth blocker である。

## チェック

- `make argument-focus-check`
- `make concept-term-check`
- 本文を編集した場合は `make mirror-check`
- 公開語彙を変えた場合は `make public-terms-check`
- 投稿前なら `make pre-submit`

## 出力形式

- `Public-reader diagnosis`
- `Central claim candidate`
- `Evidence hierarchy`
- `Local-to-public abstraction table`
- `Defense budget`
- `Section rewrite plan`
- `Figure story`
- `Files to update`
- `Checks run`

## Codex 実行メモ

- PDF が入力された場合は、可能ならテキスト抽出と数ページの視覚確認を行う。
- サブエージェントを使える場合は、public-only reviewer と repo-aware harness designer を分ける。
- `_paperops/refs/` と `_paperops/notes/` の作業用ドキュメントは日本語で書く。
- editorial architect として Results hierarchy / Discussion functions を先に診断し、薄い章を文体問題にしない。
- authoring intent leak が疑われる本文行は、読者向け文に翻訳できるものだけ本文へ残す。判断保留や作業計画は `% INTENT:` / `% TODO-PAPER:` または `_paperops/requests/` へ移し、`make authoring-intent-check` を実行する。
- 投稿前に実行できる追加シミュレーションがある場合は、defensive prose を増やす前に `draft-predicted-results` へ戻す。予測稿は final claim ではなく、実行 request と `xx` 置換条件を持つ scaffold として扱う。
- 本文に戻す文言は、ローカル条件数ではなく、物理的意味、機構、境界条件、読者の持ち帰りを主語にする。
- AI 初稿の定型臭だけを直す場合も、`_paperops/notes/ai-use.md` の AI 利用開示を消さない。
