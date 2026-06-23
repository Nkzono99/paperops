---
name: polish-ai-draft
description: AI 初稿、機械的な文体、過度に定型的なつなぎ、宣伝調、三点列挙、曖昧な出典、AI らしい防御的文章を、主張と証拠を変えずに論文向けに磨くときに使う。
---

# polish-ai-draft

AI 初稿の定型臭を減らし、読者に届く論文の文体へ整える。目的は AI 利用を隠すことではなく、曖昧な主張、過剰な一般化、機械的な構文を減らすことである。

Humanizer 系スキルの「AI らしい文章パターンを検出して自然に直す」発想を参考にするが、paperops では claim、evidence、AI disclosure を守ることを優先する。

## 最初に読むファイル

- 対象の本文、段落、caption、response draft
- `notes/scientific-gate.md`
- `notes/claim-evidence-map.md`
- `notes/argument-map.md`
- `notes/reviewer-model.md`
- `notes/ai-draft-polish.md`
- `notes/ai-use.md`
- `manuscript/mirror/terminology.yml`
- 必要に応じて `notes/related-work-map.md`、`refs/summaries/`

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
- figure caption が「計算したこと」だけを述べ、「読ませたい対比」を述べない。
- 結論が一般的な前向き文で終わり、論文固有の持ち帰りが弱い。

## 手順

### 1. Claim lock

まず対象段落の claim、evidence、scope、limitation を `notes/claim-evidence-map.md` と `notes/scientific-gate.md` で固定する。未登録の主張がある場合は、文体修正ではなく `/scientific-gate` または `/calibrate-claims` へ戻す。

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
- weak stress position

必要なら `notes/ai-draft-polish.md` の `AI 初稿 smell inventory` に要約する。

### 3. Rewrite

次の原則で直す。

- 一段落一機能にする。
- 文末と段落末に、その段落で読者に残したい情報を置く。
- 一般論ではなく、claim に対する evidence、warrant、boundary を主語にする。
- caveat は分散させず、必要な位置へまとめる。
- つなぎ語を増やさず、論理関係を文の配置で示す。
- 日本語原稿では、硬い論文語を保ちながらも、無内容な名詞句を削る。
- 英語原稿では、AI らしい promotional phrase、過剰な em dash、空疎な metadiscourse を減らす。

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

- 本文を編集した場合は `make mirror-check`、公開語を変えた場合は `make public-terms-check` を実行する。
- 原稿構造や claim strength を変える必要がある場合は、`/paragraph-surgery`、`/calibrate-claims`、`/scientific-gate` へ戻す。
- `notes/ai-use.md` の AI 利用ログや開示文案を消さない。
