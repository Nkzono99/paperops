---
name: note-writing-session
description: 作業セッションの終了近くにセッション進捗を記録する。handoff、todo、セッションノートを更新。
---

# note-writing-session

作業セッションの終了近くにこのスキルを使用する。

## 必須更新

1. `notes/sessions/` 配下に短いセッションノートを追加する（ディレクトリが存在しなければ作成する）。
2. `notes/handoff.md` を更新する。
3. `notes/todo.md` を更新する。
4. 重要な決定が行われた場合、`notes/decision-log.md` に追加する。
5. 知見の更新があれば `notes/project-brief.md`、`notes/contribution-claims.md`、`notes/scientific-gate.md`、`notes/related-work-map.md`、`notes/source-reach.md`、`notes/claim-evidence-map.md` も更新する。
6. 読者想定、投稿先、査読者の懸念が変わった場合は `notes/reviewer-model.md` を更新する。
7. 模擬査読、実査読コメント、response letter 方針が変わった場合は `notes/peer-review.md` を更新する。
8. AI が文献、解析、コード、図表、投稿文面、査読・返答案に関与した場合は `notes/ai-use.md` を更新する。AI 初稿の文体 polish を行った場合は `notes/ai-draft-polish.md` に claim lock と変更範囲を残す。
9. データ、解析環境、図表生成、共有 artifact が変わった場合は `notes/reproducibility.md` を更新する。
10. 公開本文に出さない run label、export 名、directory 名、script 名、artifact 名などは、本文ではなく `notes/reproducibility.md`、`notes/handoff.md`、`refs/` の日本語作業メモに分離して記録する。

## 推奨出力

- 何を執筆・改訂したか
- どのファイルが変更されたか
- 何がブロックまたは不確実なまま残っているか
- 次のセッションでの最初のタスク

## Codex 実行メモ

- `notes/handoff.md`、`notes/todo.md`、必要に応じて `notes/decision-log.md` を更新する。
- 関連研究、研究動向、反論文献の判断が変わった場合は `notes/related-work-map.md` に残す。
- 外部 source channel、raw capture、credential risk、到達経路の判断が変わった場合は `notes/source-reach.md` に残す。
- 中心主張の準備状態や人間承認が変わった場合は `notes/scientific-gate.md` に残す。
- 模擬査読や reviewer response の進捗は `notes/peer-review.md` に残す。
- データ、解析環境、図表生成、共有 artifact が変わった場合は `notes/reproducibility.md` を更新する。
- 恒久的な判断と一時的な作業メモを混ぜない。
- `refs/` と `notes/` の作業用ドキュメントは日本語で書き、内部 provenance 語を公開本文へ戻さない。
- 原稿構造、参考文献、ミラー状態を変えた場合は `make ci` または該当チェックを実行する。
