---
name: open-paper-scan
description: 論文プロジェクト、原稿、執筆ハーネスを俯瞰し、発散的な改善案、構造的な違和感、逆張り仮説、未言語化のテーマを出す。ユーザーが「俯瞰的に見て」「meta 的に」「普通に眺めて違和感」「発想を広げたい」「まだ記録や実装はしない」と頼んだとき、または改善指示が局所修正に固着しそうなときに使う。
---

# open-paper-scan

論文プロジェクト、公開原稿、執筆ハーネスを broad outside reviewer として眺め、まだ採用しない改善の種を出すために使う。

この skill は発想のための open scan であり、管理や修正の workflow ではない。デフォルトでは本文編集、`notes/` や `refs/` への記録、Issue 作成、`pops feedback`、上流フィードバック作成を実行しない。ユーザーが記録・調査・実装を求めたら、出た idea のうち最大 1-2 件だけを後段 skill へ渡す。

## 入力

- ユーザーが指定した PDF、TeX、section、README、notes、または scope
- scope が未指定なら、`README.md`、`AGENTS.md`、`CLAUDE.md`、`notes/project-brief.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`manuscript/ja/sections/`、`manuscript/en/sections/`、`.agents/skills/` を薄く横断する
- 公開読者視点を保つ必要がある場合は、最初は公開原稿と図表 caption だけを読む

## 目的

- 一番新しい摩擦や目についた bug に早く閉じず、設計思想、読者体験、主張設計、評価不能性、管理過多を見る。
- 既存 skill、note、Issue、check script の形に idea を早く押し込まない。
- 「直すべき問題」だけでなく、削除、統合、問いの置き換え、読者モデルの変更、図表 story の変更を候補に入れる。
- 採用判断の前に、idea の novelty、possible evidence、risk、rough horizon を軽く見積もる。

## 手順

### 1. Broad outside scan

まず外部レビュワーとして見る。repo 内の慣習や直近の失敗記録に早く寄せず、「この論文プロジェクトやハーネスが変だとしたらどこか」を探す。

見る観点:

- 読者が最初に受け取る promise と、実際の本文や作業導線がずれていないか
- 強い主張、補助証拠、境界条件、再現性情報が同じ重みで並んでいないか
- skill や script が多すぎて、agent の判断を助けるより管理対象を増やしていないか
- note や refs が memory ではなく、単なる保管箱になっていないか
- 人間が判断すべき箇所と agent が処理できる箇所が混ざっていないか

### 2. Thin horizontal read

完全な棚卸しはしない。`rg` やファイル一覧で README、AGENTS / CLAUDE、主要 notes、原稿 outline、skills、scripts、tests を薄く読み、違和感を探す。

読んだ範囲は出力で短く明記する。読んでいない範囲を推測で埋めない。

### 3. Raw Ideas を発散する

3-7 件を目安に、まだ failure class や実装 ticket に固定しない改善案を出す。

混ぜる観点:

- manuscript structure / claim hierarchy
- reader model / venue fit
- figure story / evidence selection
- AI draft failure mode
- notes / refs / handoff memory
- skill design / prompt routing
- evaluation / checks
- operator burden
- privacy / external sharing
- update / upstream feedback
- deletion / consolidation

### 4. Anti-fixation pass

今見えている既存 skill、check、note、issue に引っ張られすぎていないかを点検し、別フレーミングを最低 1 つ出す。

例:

- 「新しい check を足す」ではなく「check しなくてよい構造へ変える」
- 「note を増やす」ではなく「note を減らして本文の問いを鋭くする」
- 「AI の出力を修正する」ではなく「AI に渡す task boundary を変える」
- 「証拠不足を埋める」ではなく「主張の射程を変える」

### 5. Ideas を採用しない

各 idea に以下を短く付ける:

- rough horizon: now / next / later
- novelty: low / medium / high
- possible evidence: 何を見れば idea の妥当性を調べられるか
- risk: 実装した場合の副作用、overhead、overclaim、privacy risk

### 6. Routing Hints だけを出す

ユーザーが次に記録・調査・実装を求めた場合の渡し先を示す。最大 1-2 件に絞る。

候補:

- `/audit-ai-draft`: AI 初稿を論旨設計へ戻す
- `/contextualize-conditions`: 条件数や case count を論文上の役割へ翻訳する
- `/design-manuscript-claims`: 原稿全体を主張中心に再設計する
- `/review-public-manuscript`: 公開原稿だけで外部読者視点の詰まりを検出する
- `/improve-writing-harness`: project-local の摩擦を実装で直す
- `/feedback-paper-harness`: 再利用可能な改善を上流へ戻す
- `notes/claim-evidence-map.md`、`notes/argument-map.md`、`notes/condition-context-map.md`、`notes/reviewer-model.md`: 記録が必要になった後の置き場所

## 出力形式

- `Open Scan`: 外部レビュワー視点の違和感。読んだ範囲も明記する。
- `Raw Ideas`: まだ採用しない改善案を 3-7 件。
- `Counterframes`: 別の見方、逆張り、削除/統合案。
- `Routing Hints`: 後段へ渡すならどの idea をどこへ渡すか。
- `Do Not Record Yet`: まだ notes、Issue、実装にしない理由。

## 判断基準

- 発想を recordable にしすぎない。最初から capability、failure class、next command を埋めようとしない。
- 一番新しい摩擦だけに寄らない。設計思想、誘因、責務分離、評価不能性、管理過多を見る。
- 管理のためのチェックリストは gate として使い、generator にしない。
- 「良さそう」だけで実装しない。実装や note 化は後段で evidence、evaluation、guard を持たせる。
- privacy と external sharing を守る。未サニタイズ情報を web 検索語、Issue、PR、上流 feedback へ出さない。
- `refs/` と `notes/` に後で作る作業用ドキュメントは日本語で書く。

## Codex 実行メモ

- ユーザーが「実装して」「記録して」と明示していない場合、この skill の実行中にファイルを編集しない。
- 改善指示が曖昧なときほど、すぐ `apply_patch` や `make` へ進まず、この scan の出力で発散と収束を分ける。
- 後段へ進む場合は Raw Ideas を全部持ち込まず、最大 1-2 件に絞ってから該当 skill を使う。
