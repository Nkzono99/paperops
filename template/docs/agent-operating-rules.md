# エージェント運用ルール

## セッション開始

1. `resume-session` を実行する。
2. `docs/project-brief.md` と `notes/session-context.md` を読む。
3. バイリンガルコンテンツを編集する前に `manuscript/mirror/status.md` を確認する。

## 編集ルール

- `manuscript/shared/figures/generated/` を直接編集しない。
- `refs/local/locations.toml` をコミットしない。
- ユーザーがクラスレベルの更新を明示的にリクエストしない限り、`manuscript/shared/style/journal.cls` を変更しない。

## セッション終了

1. `note-writing-session` を実行する。
2. `notes/handoff.md` を更新する。
3. `notes/todo.md` を更新する。
4. 原稿構造や参考文献が変更された場合は `make ci` を実行する。
