# Glob: notes/**/*

## セッションノートルール

- `notes/handoff.md` はセッション開始時にフックによって読み込まれる。常に最新の状態を維持する。
- 恒久的な決定は `notes/decision-log.md` に記録する。チャット履歴だけに残さない。
- `notes/sessions/` 配下のセッションファイルは `YYYY-MM-DD-session.md` 形式を使用する。`/note-writing-session` が初回実行時にディレクトリを作成する。
- `notes/todo.md` には直近の 3〜5 タスクを反映する。バックログにしない。
- `notes/project-brief.md` と `notes/contribution-claims.md` は知見の要約であり、原稿の変化に合わせて更新する。
- `notes/reproducibility.md` は公開データ、計算環境、図表 provenance、既知の非再現ステップを記録する。データ、解析コマンド、図表生成方法、共有 artifact が変わった場合に更新する。
