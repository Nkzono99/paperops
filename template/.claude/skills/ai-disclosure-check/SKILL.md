---
name: ai-disclosure-check
description: notes/ai-use.md と投稿先ポリシーに照らして、AI 利用開示・人間検証・謝辞/Methods 文案を点検する。
argument-hint: "[venue-policy-path-or-url]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# ai-disclosure-check

AI 利用ログ、投稿先ポリシー、人間検証の証跡を点検する。

## 最初に読むファイル

- `notes/ai-use.md`
- `notes/reproducibility.md`
- `manuscript/venue.md`
- 投稿先の AI policy（ユーザーが渡した URL/PDF/テキストがあれば）

## 手順

1. AI の use type を language editing / translation / literature summary / code / figure / review に分類する。
2. 引用、解析、コード、図表、画像に AI が関与した箇所の human verification を確認する。
3. 投稿先 policy に応じて acknowledgement / methods / cover letter / none を切り分ける。
4. `notes/ai-use.md` の disclosure draft を更新する。
5. 必要なら `notes/reproducibility.md` に検証証跡を追加する。

## 注意

投稿先ポリシーは変わりうる。最新情報が必要な場合は公式資料を確認し、確認日を `notes/ai-use.md` に残す。

## 出力

- AI use summary
- Missing verification
- Disclosure placement
- Draft disclosure text
- Updated files
