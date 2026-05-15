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

パッケージ化後は `uvx` から console script を実行する:

```sh
uvx --from paper-harness-cli pops version
```

新規プロジェクトでも日常運用でも、`pops` は同じ `uvx` 経由で実行する:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

`pops init` / `pops setup` は `.pops/manifest.toml` を作成・採用するが、CLI 用の project-local `.venv` や `pops` は作成しない。
`.venv` は論文プロジェクト側の Python 実行環境が必要な場合に `make venv` で作成する。

以後のコマンド例で `pops ...` と書く場合も、標準動線では `uvx --from paper-harness-cli pops ...` として実行する。

## コマンド

- `pops init [path]`: bundled scaffold から新規論文リポジトリを作成し、`.pops/manifest.toml` を追加する。
- `pops setup [path]`: 既存論文リポジトリに `.pops/manifest.toml` を追加する。
- `pops setup <git-url> --path <dir>`: 既存 Git リポジトリを clone してから setup する。
- `pops doctor [path]`: 必須ディレクトリ、`.pops` 管理情報、Git / make、workflow placeholder、ローカル設定ファイルの状態を確認する。
- `pops update-paperops`: bundled scaffold または `--source` で指定した scaffold から、管理対象ハーネスファイルの更新計画を表示する。
- `pops update-paperops --apply`: 不足している管理対象ファイルだけを追加する。
- `pops update-paperops --apply --force`: 差分がある管理対象ファイルも上書きする。実行前に plan を確認すること。
- `pops update-paperops --only AGENTS.md,.claude/skills`: 対象 prefix を絞り込む。
- `pops update-paperops --template-ref <ref>`: 適用した scaffold の commit/ref を `.pops/manifest.toml` に記録する。`--source` が Git worktree 内なら、`--apply` 時に可能な限り自動検出する。
- `pops update-paperops --adopt`: 現在のプロジェクトを CLI 管理対象として採用し、`.pops/manifest.toml` を更新する。既存 manifest の未知 key や `template_ref` は保持する。
- `pops update-harness`: `update-paperops` の互換 alias。
- `pops migrate [path]`: 旧 scaffold 由来のプロジェクトに `.pops` 管理情報を追加する計画を表示する。
- `pops migrate --apply`: `.pops/manifest.toml` を作成する。
- `pops feedback`: 上流 `paperops` へ戻す改善フィードバックの下書きを出力する。
- `pops links list [path]`: `refs/links.toml` に登録された外部 project / directory link を表示する。`--resolve-local` を付けた場合だけ `refs/local/locations.toml` の実パスも表示する。
- `pops links check [path]`: `refs/links.toml` の schema、link id、kind、`location_ref` と `refs/local` の対応を検証する。
- `pops version`: CLI と上流情報を表示する。
- `pops --version`: `pops version` と同じ情報を表示する。

## 更新通知

TTY 上で通常コマンドが成功した場合、`pops` は1日1回を上限に PyPI の `paper-harness-cli` 最新版を確認する。新しい版がある場合や、`.pops/manifest.toml` に記録された適用済み scaffold version が実行中の `pops` より古い場合は、`uvx --from paper-harness-cli pops update-paperops --plan` と `/update-paperops` スキルで upgrade chain を確認するよう通知する。

この確認は非阻害で、ネットワーク取得に失敗してもコマンド結果には影響しない。無効化する場合は `POPS_DISABLE_VERSION_CHECK=1` を設定する。

## Versioned upgrade chain

後方互換性を最新 `pops` に積み続けないため、`update-paperops` は versioned upgrade chain を持つ。
まず plan を確認する:

```sh
uvx --from paper-harness-cli pops update-paperops --plan
```

必要に応じて checkpoint ごとの `pops` を exact version で呼び替える:

```sh
uvx --from paper-harness-cli pops update-paperops --apply-chain
uvx --from paper-harness-cli pops update-paperops --target 0.3 --apply-chain
```

major version を跨ぐ chain は既定では停止する。計画を確認したうえで明示的に許可する:

```sh
uvx --from paper-harness-cli pops update-paperops --target latest --allow-major --apply-chain
```

詳しい保持方針は [`docs/upgrade-policy.md`](upgrade-policy.md) を参照する。

## 更新対象

`update-paperops` が扱うのは、下流プロジェクトのユーザー向けハーネス面に限定する:

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

## Link registry

paper draft が runops project や外部ディレクトリを参照する場合、共有可能な link intent は `refs/links.toml` に、個人環境の絶対パスは ignored な `refs/local/locations.toml` に分離する。`pops links check` は `refs/links.toml` と `refs/local/locations.example.toml` の対応を確認し、ローカルパスを共有ファイルへ混ぜずに運用できるかを検査する。

`kind = "runops_project"` の link は、runops MCP から publication export、analysis artifact、survey summary、paper request queue を確認する入口として扱う。paper draft 側で発生した追加解析・図表・追加実験要望は `notes/research-requests.md` に記録し、`runops.paper.request.draft` で schema と id の衝突を確認してから runops project 側の `research/paper_requests.toml` に handoff する。
