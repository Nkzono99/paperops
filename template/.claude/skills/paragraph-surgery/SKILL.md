---
name: paragraph-surgery
description: 段落単位で old-to-new flow、topic sentence、stress position、1 paragraph 1 function を整える。
argument-hint: "[section-or-block-id]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# paragraph-surgery

段落を読者期待に沿う流れへ整える。科学的意味を変える場合は先に確認する。

## 観点

- 1 paragraph 1 function: context / claim / evidence / warrant / limitation / transition
- old-to-new flow: 既知情報から新情報へ進む
- stress position: 文末と段落末に重要な新情報を置く
- topic sentence: 段落の役割を冒頭で示す
- local cohesion: 指示語、主語、用語が前後でつながる

## 手順

1. 対象 block の各段落に機能ラベルを付ける。
2. 段落ごとに詰まり、重複、飛躍、文末の弱さを指摘する。
3. 科学的意味を保った rewrite plan を出す。
4. 明示依頼がある場合のみ `manuscript/ja/` を編集する。
5. 必要に応じて EN mirror を `/sync-ja-en` で同期する。

## 出力

- Paragraph function map
- Surgery plan
- Edited files
- 残る scientific question
- 検証コマンド
