# 配布

このリポジトリは論文執筆ハーネスの source of truth である。
下流プロジェクトの作成導線は `pops init` に統一する。
`template/` は Python パッケージ `paper-harness-cli` の bundled scaffold として配布する。

## リポジトリの役割

- ソースリポジトリ: `Nkzono99/paperops`
  - `template/` 配下の scaffold source
  - `src/paperops/` 配下の `pops` CLI
  - 再利用可能 workflow、Issue フォーム、テンプレート保守 skill
  - 変更ポリシー、トリアージルール、リリースノート

## 初期化モデル

新規論文プロジェクトは CLI から作成する:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
pops setup
pops doctor
```

既存プロジェクトは `.pops/manifest.toml` を追加して CLI 管理へ寄せる:

```sh
pops migrate --apply
pops doctor
```

## 更新モデル

下流プロジェクトでは `pops update-harness` を使って、管理対象ハーネスファイルの更新計画を確認する。

```sh
pops update-harness --dry-run
pops update-harness --apply
```

`update-harness` は `AGENTS.md`、`CLAUDE.md`、`Makefile`、`scripts/`、`.agents/`、`.claude/`、`.github/ISSUE_TEMPLATE/` などのハーネス管理面だけを扱う。
`manuscript/`、`notes/`、`refs/`、`submission/` は下流プロジェクト固有内容として自動上書きしない。

## PyPI 公開モデル

`.github/workflows/publish-pypi.yml` は、release publish または手動 dispatch で `paper-harness-cli` を PyPI に公開する。

workflow は build job と publish job を分ける:

- build job: `python -m build` で distribution を作成し、`twine check` で検証する。
- publish job: build artifact を取得し、PyPI Trusted Publishing で `pypa/gh-action-pypi-publish@release/v1` から公開する。

PyPI 側では trusted publisher として以下を設定する:

- Project: `paper-harness-cli`
- Repository: `Nkzono99/paperops`
- Workflow: `.github/workflows/publish-pypi.yml`
- Environment: `pypi`

## 運用ルール

- `template/` の変更はまずこのリポジトリで行う。
- 配布専用リポジトリを編集・同期対象にしない。
- ユーザーに影響する CLI / scaffold 変更は `CHANGELOG.md` に記録する。
- 下流互換性に影響する変更は `pops migrate` または `pops update-harness` の挙動と docs に反映する。
