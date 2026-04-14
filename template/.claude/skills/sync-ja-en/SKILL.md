---
name: sync-ja-en
description: 日本語と英語の原稿をブロックレベルで同期する。ブロックが不整合の場合や ja/ セクション編集後に使用。
argument-hint: "[section-file]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# sync-ja-en

日本語と英語の原稿をブロックレベルで整合させるためにこのスキルを使用する。

## 最初に読むファイル

- `manuscript/mirror/map.toml`
- `manuscript/mirror/terminology.yml`
- `manuscript/mirror/status.md`
- `manuscript/mirror/change-queue.md`

## 責務

1. `status.md` に別段の記載がない限り、日本語をソースオブトゥルースとして扱う。
2. `% block: ...` 識別子を使用して、対応するファイルをブロック単位で比較する。
3. リクエストされたブロックまたは明らかに古いブロックの英語テキストのみを更新する。
4. 英語テキストが科学的意味を変更する場合、その変更を日本語に反映するか、`change-queue.md` に記録する。
5. 意味のある同期作業の後に `status.md` を更新する。

## 補助ツール

- `templates/drift-report.md`
- `scripts/sync_blocks.py`

両言語を盲目的に上書きしないこと。ブロック ID と科学的意図を保持する。
