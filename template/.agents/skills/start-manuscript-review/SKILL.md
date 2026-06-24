---
name: start-manuscript-review
description: Use when starting a human PDF or TeX manuscript review session.
---

# start-manuscript-review

人間が PDF または TeX を読みながら `manuscript/ja` / `manuscript/en` を直接修正するレビューセッションを始めるときに使用する。

このスキルは本文を編集しない。作業 branch を安全に用意し、人間が低い認知負荷でレビューできる方法を短く提示する。

## 最初に確認するもの

1. `git rev-parse --show-toplevel`
2. `git remote -v`
3. `git status --short --branch`
4. `manuscript/mirror/status.md`
5. 必要に応じて `notes/handoff.md` と `notes/todo.md`

## Branch 方針

- 既定の branch 名は `review/manuscript-YYYY-MM-DD` とする。
- ユーザーが branch 名を指定した場合はそれを使う。
- 作業ツリーが clean なら `git checkout -b <branch>` で開始する。
- 既に同名 branch がある場合は `git checkout <branch>` で移動する。
- 未コミット変更がある場合は、勝手に stash / commit / checkout しない。現在の変更を持ったまま続けるか、別作業として整理するかを短く確認する。
- nested private repo 運用を考慮し、対象 repo と remote を必ず表示してから branch を切る。

## 人間向けレビューガイド

開始後、以下をそのまま短く案内する:

- PDF または TeX を通読し、直せる表現は `manuscript/ja/**/*.tex` に直接直す。
- `manuscript/mirror/status.md` に別段の記載がなければ、科学的 source of truth は `manuscript/ja/` とする。
- `% block: ...` は削除、変更、番号振り直しをしない。
- 直しきれない違和感は、近くの TeX 行に短いコメントで残す:
  - `% REVIEW: ここはまだ弱い`
  - `% AI: 論文調に整えて`
  - `% Q: 断言しすぎ？`
  - `% KEEP?: この段落いる？`
  - `% TODO-PAPER: 追加すべき根拠`
- 投稿先公式テンプレート側の `submission/<venue>/` を直接 source of truth にしない。
- レビュー終了後は `/collect-manuscript-review` を実行して、diff と inline comment を `notes/reviews/review-YYYY-MM-DD.md` に回収する。

## 推奨する開始時出力

- 対象 repo と remote
- 現在 branch とレビュー branch
- source-of-truth 言語
- レビュー対象の候補ファイル
- 上記の人間向けレビューガイド
- 終了後に実行する `/collect-manuscript-review` の案内

## 注意

- このスキルでは原稿修正を代行しない。人間が読みながら自然に残した diff と comment を、後続の `/collect-manuscript-review` が回収する。
- branch 操作以外の git 変更は行わない。
- build が必要な場合だけ `make build-ja` / `make build-en` または PowerShell PDF wrapper を案内する。

## Codex 実行メモ

- まず `git rev-parse --show-toplevel`、`git remote -v`、`git status --short --branch`、`manuscript/mirror/status.md` を確認する。
- clean な作業ツリーなら `review/manuscript-YYYY-MM-DD` またはユーザー指定名へ `git checkout -b` で移動する。
- 未コミット変更がある場合は、勝手に stash / commit / branch 移動をしない。
- ユーザーには `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% TODO-PAPER:` の inline comment と `% block:` 保持ルールを短く案内する。
- レビュー終了後は `/collect-manuscript-review` で diff と inline comment を回収するよう案内する。
