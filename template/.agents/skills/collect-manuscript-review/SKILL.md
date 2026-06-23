---
name: collect-manuscript-review
description: TeX 直編集 diff と inline review comment を回収し、レビュー台帳を作成して、必要に応じて source-of-truth 原稿と EN mirror へ反映する。
---

# collect-manuscript-review

人間が `/start-manuscript-review` 後に TeX を直接編集し、inline comment を残したあとに使用する。

`notes/reviews/review-YYYY-MM-DD.md` は人間が最初から構造化して書く入力フォームではなく、`git diff` と TeX コメントから生成される作業台帳として扱う。

## 回収対象

- `git diff -- manuscript/ja manuscript/en`
- TeX inline comment:
  - `% REVIEW: ...`
  - `% AI: ...`
  - `% Q: ...`
  - `% KEEP?: ...`
  - `% TODO-PAPER: ...`
- 近傍の `% block: ...`
- `manuscript/mirror/status.md`
- `manuscript/mirror/map.toml`
- 必要に応じて `manuscript/mirror/terminology.yml`

## 回収手順

1. `git status --short --branch` で review branch と変更範囲を確認する。
2. `manuscript/mirror/status.md` で source-of-truth 言語を確認する。
3. 次のコマンドでレビュー台帳を生成する:

   ```sh
   python scripts/collect-manuscript-review.py --root . --output notes/reviews/review-YYYY-MM-DD.md
   ```

4. 生成された台帳を読み、以下を短く要約する:
   - 直接編集されたファイルと block
   - inline comment の論点
   - 人間の表現修正から推定できる好み
   - 科学的意味が変わる可能性のある変更
   - open question
5. 本文を直す前に、反映方針を提示する。科学的意味、主張、証拠、図表、追加解析に関わる指摘は `/integrate-writing-feedback` に渡し、`review/feedback/` の feedback card から上流へ遡らせる。ユーザーが明示的に「反映して」「修正して」「apply」などを依頼している場合も、本文だけで済む修正か feedback card 化が必要な修正かを分ける。

## Apply フェーズ

原稿修正に進む場合:

1. `manuscript/mirror/status.md` に別段の記載がない限り、`manuscript/ja/` を科学的 source of truth として編集する。
2. `% block: ...` を保持する。削除、改名、番号振り直しはしない。
3. 解決済み inline comment は削除する。未解決のものは台帳、`notes/todo.md`、または原稿内 comment のいずれに残すか明記する。
4. 人間の直接編集 diff は尊重し、意図が曖昧な箇所だけ open question に戻す。
5. claim / evidence / gate に影響する変更は、`/integrate-writing-feedback` で feedback card と上流 card を更新してから本文へ反映する。
6. JA の科学的意味を変えた場合は、対応する `manuscript/en` block を更新するか、`manuscript/mirror/change-queue.md` に残す。
7. `submission/<venue>/` を source of truth として編集しない。

## 検証

- 原稿本文または EN mirror に反映したら `make mirror-check` を実行する。
- 引用、refs、構造、build に触れた場合は `make ci` を実行する。
- レビュー台帳だけを生成して本文を変えていない場合は、検証コマンドを省略してよい。

## 出力形式

- `Review ledger`: 生成または更新した `notes/reviews/review-YYYY-MM-DD.md`
- `Collected comments`: marker、file、line、block の要約
- `Diff interpretation`: 直接編集から見える表現方針
- `Apply plan`: source-of-truth、対象 block、EN mirror への反映要否
- `Open questions`: 人間判断が必要な論点
- `Edits applied`: 実際に変更したファイル
- `Validation`: 実行したコマンドと結果

## 注意

- 台帳はレビュー回収用の中間生成物である。コミット対象にするかはプロジェクト運用に従う。
- 原稿の科学的主張を勝手に強めない。
- 大きな構成変更、引用追加、図表差し替えが必要な場合は、単独の review apply に混ぜず、別タスクとして切り出す。

## Codex 実行メモ

- `git status --short --branch`、`manuscript/mirror/status.md`、`manuscript/mirror/map.toml` を確認する。
- `python scripts/collect-manuscript-review.py --root . --output notes/reviews/review-YYYY-MM-DD.md` で台帳を生成する。
- `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% TODO-PAPER:` を file / line / `% block:` に紐付けて読む。
- 本文反映を依頼されている場合は、まず source-of-truth 側を整え、解決済み inline comment を削除し、必要な `manuscript/en` block を同期する。
- 原稿本文または mirror を変えたら `make mirror-check` を実行する。構造、引用、refs、build に触れた場合は `make ci` を実行する。
