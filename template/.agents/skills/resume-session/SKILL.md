---
name: resume-session
description: 執筆セッション開始時に原稿の状態を要約し、ミラーのドリフトを特定し、次のステップを提案する。
---

# resume-session

執筆セッション開始時に、現在状態と次に安全な作業を短く復元する。再開時に全ビューを読み込んで重くしすぎず、常時読む入口と必要時に読む詳細を分ける。

## 常時読む

- `_paperops/notes/handoff.md`
- `_paperops/notes/todo.md`
- `_paperops/notes/open-questions.md`
- `_paperops/notes/project-brief.md`
- `manuscript/mirror/status.md`
- `_paperops/model/issues/feedback/`
- `_paperops/model/issues/`

## 必要時に読む

- claim / evidence の判断が必要: `_paperops/model/research/README.md`、`_paperops/model/research/README.md`、`_paperops/notes/views/claim-evidence-map.md`
- scientific-gate で止まった claim を見る: `_paperops/notes/views/scientific-gate.md`、`_paperops/model/research/gates/`
- 関連研究や外部 source が次作業: `_paperops/notes/related-work-map.md`、`_paperops/notes/source-reach.md`、`_paperops/refs/`
- reviewer / feedback loop が次作業: `_paperops/model/issues/README.md`、`_paperops/notes/views/peer-review.md`、`_paperops/notes/reviewer-model.md`
- AI draft や開示が関係する: `_paperops/notes/ai-draft-polish.md`、`_paperops/notes/ai-use.md`

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
- `_archives/` は通常読まない。明示的な restore / inspect / compare 指示がある場合だけ扱う。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
