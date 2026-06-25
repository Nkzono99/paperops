# 配布

`paperops` は論文執筆ハーネスの source of truth である。`template/` は Python パッケージ `paper-harness-cli` に bundled scaffold として入る。

## 作成と更新

新規論文プロジェクト:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

既存プロジェクト:

```sh
uvx --from paper-harness-cli pops setup
uvx --from paper-harness-cli pops doctor
```

下流更新:

```sh
uvx --from paper-harness-cli pops update-paperops --dry-run
uvx --from paper-harness-cli pops update-paperops --apply
uvx --from paper-harness-cli pops update-paperops --plan
```

`update-paperops` は `AGENTS.md`、`CLAUDE.md`、`Makefile`、`contracts/`、`scripts/`、`.agents/`、`.claude/`、`.github/ISSUE_TEMPLATE/` などのハーネス管理面だけを扱う。原稿、notes、refs、カード層、`manuscript/writing-profile.yml` は下流固有内容として自動上書きしない。

## PyPI

`.github/workflows/publish-pypi.yml` が release publish または手動 dispatch で `paper-harness-cli` を PyPI に公開する。公開対象は `main` 由来の commit に限定する。

PyPI Trusted Publishing の設定:

- Project: `paper-harness-cli`
- Repository: `Nkzono99/paperops`
- Workflow: `.github/workflows/publish-pypi.yml`
- Environment: `pypi`

workflow は distribution build / twine check / scaffold package boundary check を行ってから公開する。

## リリース

1. `pyproject.toml` と `src/paperops/__init__.py` の version を上げる。
2. `CHANGELOG.md` の `Unreleased` を release section に移す。
3. `python scripts/check-release-version-truth.py --release-version <version> --github-repo Nkzono99/paperops` を通す。
4. 必要に応じて `make smoke`、`python -m build`、`twine check dist/*` を通す。
5. `main` を push し、`v<version>` tag と GitHub Release を作る。
6. PyPI publish workflow の成功を確認する。

運用方針は [change-policy.md](change-policy.md) を正本にする。
