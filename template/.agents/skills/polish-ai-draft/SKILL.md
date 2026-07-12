---
name: polish-ai-draft
description: Use when polishing AI-like draft prose without changing claims or evidence.
---

# polish-ai-draft

AI 初稿の定型臭を減らし、読者に届く論文の文体へ整える。目的は AI 利用を隠すことではなく、曖昧な主張、過剰な一般化、機械的な構文を減らすことである。

Humanizer 系スキルの「AI らしい文章パターンを検出して自然に直す」発想を参考にするが、paperops では claim、evidence、AI disclosure を守ることを優先する。

## 最初に読むファイル

- 対象の本文、段落、caption、response draft
- `_paperops/notes/views/scientific-gate.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/argument-map.md`
- `_paperops/notes/views/concept-terms.md`
- `_paperops/notes/reviewer-model.md`
- `_paperops/notes/ai-draft-polish.md`
- `_paperops/notes/ai-use.md`
- `manuscript/mirror/terminology.yml`
- 必要に応じて `_paperops/notes/related-work-map.md`、`_paperops/refs/summaries/`

## 絶対ルール

- 新しい科学的主張を追加しない。
- 数値、単位、分母、条件名、引用、figure reference を推測で直さない。
- 曖昧な出典を自然な言い回しで隠さない。具体的な citation がなければ `要確認` として残す。
- AI 利用開示を消したり、AI 生成でないように見せる目的では使わない。
- `scientific-gate` で `analysis-needed` または `assumption-blocked` の claim を、文体だけで `ready-to-write` に見せない。

## AI 初稿 smell

以下を探す。

- 抽象名詞と大きな意義を重ねるだけで、何を示したかが薄い。
- `重要である`、`示唆する`、`貢献する`、`包括的`、`堅牢` などが evidence なしで出る。
- `A, B, C` の三点列挙や、同じ構文の箇条書きが続く。
- `一方で`、`さらに`、`なお`、`このことは` が機械的に段落をつなぐ。
- 防御的 caveat が各段落に散り、中心主張の位置がぼやける。
- 曖昧な主語、曖昧な出典、`先行研究では` だけの文がある。
- `この claim を強めるための追加作業`、`後で埋める`、`authoring note` のように、AI Writer の執筆意図や作業計画が本文 prose になっている。
- figure caption が「計算したこと」だけを述べ、「読ませたい対比」を述べない。
- 結論が一般的な前向き文で終わり、論文固有の持ち帰りが弱い。
- concept-term compression が多い。強い hyphen / slash compound や英語名詞句が、説明なしに概念名として並ぶ。

## 手順

### 1. Claim lock

まず対象段落の claim、evidence、scope、limitation を `_paperops/notes/views/claim-evidence-map.md` と `_paperops/notes/views/scientific-gate.md` で固定する。未登録の主張がある場合は、文体修正ではなく `/scientific-gate` または `/calibrate-claims` へ戻す。

### 2. Smell annotation

対象文を、以下のどれが問題かに分類する。

- vague significance
- formulaic transition
- triad / list inflation
- vague attribution
- defensive clutter
- overclaim
- underclaim
- local provenance term
- concept-term compression
- authoring intent leak
- weak stress position

必要なら `_paperops/notes/ai-draft-polish.md` の `AI 初稿 smell inventory` に要約する。

### 3. Rewrite

次の原則で直す。

- 一段落一機能にする。
- 文末と段落末に、その段落で読者に残したい情報を置く。
- 一般論ではなく、claim に対する evidence、warrant、boundary を主語にする。
- caveat は分散させず、必要な位置へまとめる。
- `_paperops/notes/views/concept-terms.md` で accepted ではない概念語は、普通の文へほどく。accepted の場合も表記を一つに固定し、頻出させすぎない。
- つなぎ語を増やさず、論理関係を文の配置で示す。
- 日本語原稿では、硬い論文語を保ちながらも、無内容な名詞句を削る。
- 英語原稿では、AI らしい promotional phrase、過剰な em dash、空疎な metadiscourse を減らす。
- AI の判断保留や作業計画は自然な本文に言い換えて隠さない。公開読者に必要な内容なら reader-facing claim / limitation / future work へ翻訳し、未解決なら `% INTENT:` / `% TODO-PAPER:`、`_paperops/notes/`、`_paperops/model/issues/` へ移す。

### 4. Integrity pass

rewrite 後に、元の claim / evidence / scope から逸脱していないか確認する。変更した数値、引用、条件名、figure reference はすべて明記する。変えていない場合も「科学的意味は変更なし」と書く。

## 出力

- `Claim lock`
- `AI-draft smell inventory`
- `Rewrite`
- `Integrity check`
- `Unresolved evidence/source issues`
- `Files updated`
- `Checks run`

## Codex 実行メモ

- 本文を編集した場合は `make mirror-check`、概念語を変えた場合は `make concept-term-check`、公開語を変えた場合は `make public-terms-check`、AI 執筆意図を整理した場合は `make authoring-intent-check` を実行する。
- 原稿構造や claim strength を変える必要がある場合は、`/paragraph-surgery`、`/calibrate-claims`、`/scientific-gate` へ戻す。
- `_paperops/notes/ai-use.md` の AI 利用ログや開示文案を消さない。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
