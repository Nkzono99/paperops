---
name: release
description: paperops のリリースノート作成、バージョン更新、検証、コミット、タグ作成、GitHub Release 公開、PyPI publish workflow 確認まで行うときに使う。ユーザーが「リリースして」「releaseして」「リリースノートを書いて公開して」と依頼した場合に使う。
---

# release

paperops の root 層をリリースする。`template/` を直接変える場合は AGENTS.md のテンプレート変更ルールも守る。

## 手順

1. 作業ツリーとリモート状態を確認する。
   - `git status --short`
   - `git fetch --tags origin`
   - `git status -sb`
   - `git log --oneline <last-tag>..HEAD`
   - release 準備は `main` 直コミットではなく `codex/release-v<version>` などの topic branch で行う。
2. リリース種別を判断する。
   - patch: バグ修正、ドキュメント、内部整理。
   - minor: CLI / scaffold のユーザー向け機能追加や標準導線変更。
   - major: 互換性破壊、既定動作の大きな変更。
   - 判断に迷う場合は安全側で minor にする。
3. `pyproject.toml` の `[project].version` を更新する。
4. `CHANGELOG.md` の `## Unreleased` を `## <version> - YYYY-MM-DD` に移し、今回のリリースノートとして読めるように整える。
   - ユーザー向けの変更、移行手順、互換性メモを残す。
   - 空の `## Unreleased` を先頭に残す。
5. 必要に応じて docs / README の version や導線の食い違いを直す。
6. 検証する。
   - `make smoke`
   - パッケージ確認が必要なら `py -3 -m build` と `py -3 -m twine check dist/*`
7. リリース準備コミットを作る。
   - コミットメッセージ例: `<version> リリース準備`
8. topic branch を push して Pull Request を作る。
   - `git push origin HEAD`
   - `gh pr create --base main --head <branch> --title "<version> リリース準備" --body <body>`
   - `Smoke / smoke` が通ったことを確認する。
9. Pull Request を merge し、`main` を最新化する。
   - `gh pr merge --squash --delete-branch` など repo policy に合う方法を使う。
   - `git switch main`
   - `git pull --ff-only origin main`
10. tag は `origin/main` から到達可能な merge 済み commit にだけ作る。
   - `git tag -a v<version> -m "v<version>"`
   - `git push origin v<version>`
11. GitHub Release を公開する。
    - `gh release create v<version> --title "v<version>" --notes-file <release-notes-file>`
    - notes file は一時ファイルでよい。`CHANGELOG.md` の該当セクションを元にする。
12. PyPI workflow を確認する。
    - release publish で `.github/workflows/publish-pypi.yml` が走る。
    - workflow は tag commit が `origin/main` から到達可能な場合だけ publish する。
    - `gh run list --workflow publish-pypi.yml --limit 5`
    - 失敗した場合は log を見て、修正が必要なら別コミットで直す。

## 注意

- `dist/`、一時 release notes file、実行時 cache はコミットしない。
- 既存の未コミット変更がある場合は、今回のリリースに含めるかユーザー変更として残すかを明確にする。
- `main` への直接 push はしない。緊急修正でも topic branch と Pull Request を使う。
- `git push` と GitHub Release はリモート書き込みなので、ユーザーがリリースを明示した場合だけ実行する。
- PyPI への直接アップロードはしない。Trusted Publishing workflow に委譲する。
