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
uvx --from paper-harness-cli pops doctor
```

既存プロジェクトは `.pops/manifest.toml` を追加して CLI 管理へ寄せる:

```sh
uvx --from paper-harness-cli pops setup
uvx --from paper-harness-cli pops doctor
```

`pops init` / `pops setup` は `.pops/manifest.toml` を作成・採用する。CLI 実行は project-local `.venv` に固定せず、常に `uvx --from paper-harness-cli pops ...` に寄せる。
`.venv` は論文プロジェクトの Python 実行環境が必要な場合に `make venv` で作成する。

## 更新モデル

下流プロジェクトでは `pops update-paperops` を使って、管理対象ハーネスファイルの更新計画を確認する。標準実行は `uvx --from paper-harness-cli pops update-paperops ...` である。

```sh
uvx --from paper-harness-cli pops update-paperops --dry-run
uvx --from paper-harness-cli pops update-paperops --apply
```

`update-paperops` は `AGENTS.md`、`CLAUDE.md`、`Makefile`、`scripts/`、`.agents/`、`.claude/`、`.github/ISSUE_TEMPLATE/` などのハーネス管理面だけを扱う。
`manuscript/`、`notes/`、`refs/`、`submission/` は下流プロジェクト固有内容として自動上書きしない。

`refs/links.toml` と `notes/research-requests.md` は新規 scaffold では同梱するが、既存下流プロジェクトでは project 固有の link / request 台帳として扱う。取り込む場合は `pops update-paperops --apply` の自動上書きではなく、必要に応じて手動で追加し、`pops links check` で検証する。runops project link を使う場合は `/resolve-local-paths` で link を確認し、追加要望は `runops.paper.request.draft` で検証してから runops 側へ handoff する。

`pops` は TTY 上の通常実行時に PyPI の `paper-harness-cli` 最新版、実行中の `pops` version、`.pops/manifest.toml` の適用済み scaffold version を低頻度で確認し、更新がある場合は `uvx --from paper-harness-cli pops update-paperops --plan` と `/update-paperops` スキルの使用を案内する。既存の `pops update-harness` は互換 alias として残す。

下流互換性を最新 CLI に積み続けないため、更新は versioned upgrade chain で行える:

```sh
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply-chain
```

chain runner は minor ごとの checkpoint release を exact version で呼び替える。major version を跨ぐ場合は、計画確認後に `--allow-major` を明示する。
詳細は `docs/upgrade-policy.md` を参照する。

## PyPI 公開モデル

`.github/workflows/publish-pypi.yml` は、release publish または手動 dispatch で `paper-harness-cli` を PyPI に公開する。ただし公開対象は `main` 由来に限定する。release publish の場合は tag が指す commit が `origin/main` から到達可能であることを検証し、手動 dispatch の場合は `main` ref からの実行だけを許可する。

workflow は build job と publish job を分ける:

- build job: release / dispatch が `main` 由来であることを確認し、`python -m build` で distribution を作成し、`twine check` で検証する。
- publish job: build artifact を取得し、PyPI Trusted Publishing で `pypa/gh-action-pypi-publish@release/v1` から公開する。

PyPI 側では trusted publisher として以下を設定する:

- Project: `paper-harness-cli`
- Repository: `Nkzono99/paperops`
- Workflow: `.github/workflows/publish-pypi.yml`
- Environment: `pypi`

## 運用ルール

- `main` への直接 push は禁止し、変更は Pull Request 経由で取り込む。
- PR では `Smoke / smoke` を必須チェックとして通す。
- `template/` の変更はまずこのリポジトリで行う。
- 配布専用リポジトリを編集・同期対象にしない。
- ユーザーに影響する CLI / scaffold 変更は `CHANGELOG.md` に記録する。
- 下流互換性に影響する変更は `pops migrate` または `pops update-paperops` の挙動と docs に反映する。
- release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。
