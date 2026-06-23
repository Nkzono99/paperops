---
name: resume-session
description: 執筆セッション開始時に原稿の状態を要約し、ミラーのドリフトを特定し、次のステップを提案する。
---

# resume-session

執筆セッションの開始時にこのスキルを使用する。

## 最初に読むファイル

- `notes/handoff.md`
- `notes/todo.md`
- `notes/open-questions.md`
- `notes/project-brief.md`
- `notes/related-work-map.md`
- `notes/claim-evidence-map.md`
- `notes/reviewer-model.md`
- `manuscript/mirror/status.md`

## 目的

1. 現在の原稿状態を5項目以内で要約する。
2. コンテンツ変更のアクティブなソースオブトゥルースを特定する。
3. 中心主張、必須 evidence、想定読者の懸念を確認する。
4. ミラーのドリフト、refs の未完了作業、未解決の質問を指摘する。
5. 次の具体的な執筆ステップを提案する。

## 出力構成

- 現在のフォーカス
- 直近の進捗
- 直近の次のタスク
- 注視すべきリスクやドリフト

固定フォーマットが必要な場合は `templates/session-summary.md` のスタータープロンプトを使用する。

## Codex 実行メモ

- `notes/handoff.md`、`notes/todo.md`、`notes/open-questions.md`、`notes/project-brief.md`、`notes/related-work-map.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`manuscript/mirror/status.md` を優先して読む。
- 原稿編集前に ja/en のミラー状態を確認し、必要なら `make mirror-check` を実行する。
- ユーザーには、現在状態、中心主張、次に安全に進める作業、未解決リスクを短く返す。
