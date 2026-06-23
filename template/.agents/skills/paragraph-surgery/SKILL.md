---
name: paragraph-surgery
description: 段落単位で old-to-new flow、topic sentence、stress position、1 paragraph 1 function を整える。
---

# paragraph-surgery

段落を読者期待に沿う流れへ整える。科学的意味を変える場合は先に確認する。

## 観点

- 1 paragraph 1 function: context / claim / evidence / warrant / limitation / transition
- old-to-new flow: 既知情報から新情報へ進む
- stress position: 文末と段落末に重要な新情報を置く
- topic sentence: 段落の役割を冒頭で示す
- local cohesion: 指示語、主語、用語が前後でつながる
- public terminology: run label、directory name、script name、artifact name を本文の説明語にせず、読者に通じる物理条件・選別基準・診断量へ置き換える

## 手順

1. 対象 block の各段落に機能ラベルを付ける。
2. 段落ごとに詰まり、重複、飛躍、文末の弱さを指摘する。
3. 内部 provenance 語が本文に残っていないか確認し、必要なら `manuscript/mirror/terminology.yml` に置換方針を追加する。
4. 条件番号・条件数で始まる topic sentence を探し、`grouping -> contrast -> exception -> warrant` へ組み替える。
5. 科学的意味を保った rewrite plan を出す。
6. 明示依頼がある場合のみ `manuscript/ja/` を編集する。
7. 必要に応じて EN mirror を `/sync-ja-en` で同期する。

## 出力

- Paragraph function map
- Surgery plan
- Edited files
- Public terminology changes
- 残る scientific question
- 検証コマンド

## Codex 実行メモ

- 段落を context / claim / evidence / warrant / limitation / transition に分類する。
- 科学的意味を変える場合は先に計画を示す。
- 内部 provenance 語は本文から除き、必要な作業メモは `refs/` / `notes/` に日本語で残す。
- 段落末の stress position は条件数ではなく、その条件数が示す物理的意味・境界条件・機構にする。
- 本文を編集したら `make mirror-check`、必要なら `/sync-ja-en` を実行する。
