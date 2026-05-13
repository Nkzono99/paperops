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
8. タグを作る。
   - `git tag -a v<version> -m "v<version>"`
9. リモートへ push する。
   - `git push origin HEAD`
   - `git push origin v<version>`
10. GitHub Release を公開する。
    - `gh release create v<version> --title "v<version>" --notes-file <release-notes-file>`
    - notes file は一時ファイルでよい。`CHANGELOG.md` の該当セクションを元にする。
11. PyPI workflow を確認する。
    - release publish で `.github/workflows/publish-pypi.yml` が走る。
    - `gh run list --workflow publish-pypi.yml --limit 5`
    - 失敗した場合は log を見て、修正が必要なら別コミットで直す。

## 注意

- `dist/`、一時 release notes file、実行時 cache はコミットしない。
- 既存の未コミット変更がある場合は、今回のリリースに含めるかユーザー変更として残すかを明確にする。
- `git push` と GitHub Release はリモート書き込みなので、ユーザーがリリースを明示した場合だけ実行する。
- PyPI への直接アップロードはしない。Trusted Publishing workflow に委譲する。
