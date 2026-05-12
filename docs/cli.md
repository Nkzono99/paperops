# pops CLI

`pops` は、`paperops` の `template/` を論文リポジトリとして初期化し、最低限の保守操作を安定したコマンド面に寄せるための CLI である。

この CLI は将来の標準化前の薄い実行カーネルとして扱う。Agent やスキルは研究判断、原稿編集、手順選択を担当し、`pops` はファイル生成、診断、管理対象ハーネス更新のような決定的操作を担当する。

## インストールと実行

開発中は以下で実行できる:

```sh
python scripts/cli-smoke.py
```

root の smoke には CLI 検査も含める:

```sh
make cli-smoke
make smoke
```

パッケージ化後は console script を使う:

```sh
uvx --from paper-harness-cli pops version
```

新規プロジェクトでは、最初の `uvx` は bootstrap 用である:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
.venv\Scripts\Activate.ps1  # Windows / PowerShell
# source .venv/bin/activate  # macOS / Linux
pops doctor
```

`pops init` / `pops setup` は `.venv` を作成し、既定では `paper-harness-cli==<実行中のバージョン>` を project-local にインストールする。
以後の `pops` は activate した `.venv` の console script を使う。
環境構築を分ける場合は `--skip-venv` / `--skip-install`、インストール元を変える場合は `--install-spec` を使う。

## コマンド

- `pops init [path]`: bundled scaffold から新規論文リポジトリを作成し、`.pops/manifest.toml` を追加し、project-local `.venv` に `pops` を用意する。
- `pops setup [path]`: 既存論文リポジトリに `.pops/manifest.toml` を追加し、project-local `.venv` に `pops` を用意する。
- `pops setup <git-url> --path <dir>`: 既存 Git リポジトリを clone してから setup する。
- `pops doctor [path]`: 必須ディレクトリ、`.pops` 管理情報、Git / make、workflow placeholder、ローカル設定ファイルの状態を確認する。
- `pops update-harness`: bundled scaffold または `--source` で指定した scaffold から、管理対象ハーネスファイルの更新計画を表示する。
- `pops update-harness --apply`: 不足している管理対象ファイルだけを追加する。
- `pops update-harness --apply --force`: 差分がある管理対象ファイルも上書きする。実行前に plan を確認すること。
- `pops update-harness --only AGENTS.md,.claude/skills`: 対象 prefix を絞り込む。
- `pops update-harness --template-ref <ref>`: 適用した scaffold の commit/ref を `.pops/manifest.toml` に記録する。`--source` が Git worktree 内なら、`--apply` 時に可能な限り自動検出する。
- `pops update-harness --adopt`: 現在のプロジェクトを CLI 管理対象として採用し、`.pops/manifest.toml` を更新する。既存 manifest の未知 key や `template_ref` は保持する。
- `pops migrate [path]`: 旧 scaffold 由来のプロジェクトに `.pops` 管理情報を追加する計画を表示する。
- `pops migrate --apply`: `.pops/manifest.toml` を作成する。
- `pops feedback`: 上流 `paperops` へ戻す改善フィードバックの下書きを出力する。
- `pops version`: CLI と上流情報を表示する。
- `pops --version`: `pops version` と同じ情報を表示する。

## 更新対象

`update-harness` が扱うのは、下流プロジェクトのユーザー向けハーネス面に限定する:

- `AGENTS.md`
- `CLAUDE.md`
- `Makefile`
- `TROUBLESHOOTING.md`
- `scripts/`
- `.agents/`
- `.claude/`
- `.github/ISSUE_TEMPLATE/`
- `.github/PULL_REQUEST_TEMPLATE.md`

`README.md`、`notes/`、`manuscript/`、`refs/`、`submission/` はプロジェクト固有内容として自動更新対象にしない。
