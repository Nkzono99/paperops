---
name: resume-session
description: 執筆セッション開始時に原稿の状態を要約し、ミラーのドリフトを特定し、次のステップを提案する。
---

# resume-session

執筆セッション開始時に、現在状態と次に安全な作業を短く復元する。再開時に全ビューを読み込んで重くしすぎず、常時読む入口と必要時に読む詳細を分ける。

## 常時読む

- `notes/handoff.md`
- `notes/todo.md`
- `notes/open-questions.md`
- `notes/project-brief.md`
- `manuscript/mirror/status.md`
- `review/feedback/`
- `requests/`

## 必要時に読む

- claim / evidence の判断が必要: `claims/README.md`、`evidence/README.md`、`notes/views/claim-evidence-map.md`
- scientific-gate で止まった claim を見る: `notes/views/scientific-gate.md`、`claims/gates/`
- 関連研究や外部 source が次作業: `notes/related-work-map.md`、`notes/source-reach.md`、`refs/`
- reviewer / feedback loop が次作業: `review/README.md`、`notes/views/peer-review.md`、`notes/reviewer-model.md`
- AI draft や開示が関係する: `notes/ai-draft-polish.md`、`notes/ai-use.md`

## 目的

1. 現在の原稿状態を 5 項目以内で要約する。
2. content source-of-truth と ja/en mirror 状態を確認する。
3. 中心主張、必須 evidence、想定読者の懸念のうち、今の作業に関係するものだけ確認する。
4. scientific gate、refs、review feedback、requests の未完了作業を次の route に分ける。
5. 次の具体的な執筆ステップを 1-3 個に絞る。

## 出力

- 現在のフォーカス
- 直近の進捗
- 次のタスク
- 注視すべきリスクや drift

固定フォーマットが必要な場合は `templates/session-summary.md` の starter prompt を使う。

## Codex 実行メモ

- 原稿編集前に `manuscript/mirror/status.md` を確認し、必要なら `make mirror-check` を実行する。
- ユーザーには、現在状態、中心主張、次に安全に進める作業、未解決リスクを短く返す。
- 追加の view は、次作業に必要なものだけ読む。
