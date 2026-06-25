# pops CLI

`pops` は、`paperops` の scaffold を初期化・診断・更新する薄い CLI である。研究判断や原稿編集は Agent / skill が担当し、`pops` は決定的なファイル操作を担当する。

## 実行方法

標準実行は常に `uvx` 経由にする。

```sh
uvx --from paper-harness-cli pops version
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

`pops init` / `pops setup` は `.pops/manifest.toml` を作成するが、CLI 用の project-local `.venv` は作らない。`.venv` は論文プロジェクト用の Python 環境が必要な場合に `make venv` で作る。

下流の `make ci` には、argument focus、main-text figure reference、claim evidence、外部 bundle import state、research request handoff、カード層などの advisory checks も含まれる。

## コマンド一覧

- `pops init [path]`: bundled scaffold から新規論文リポジトリを作る。
- `pops setup [path]`: 既存リポジトリを `.pops` 管理に採用する。
- `pops setup <git-url> --path <dir>`: clone してから setup する。
- `pops doctor [path]`: 構造、`.pops`、Git / make、workflow placeholder、link registry を確認する。
- `pops update-paperops`: 管理対象ハーネスファイルの更新計画を表示する。
- `pops update-paperops --apply`: 不足している管理対象ファイルだけ追加する。
- `pops update-paperops --apply --force`: 差分がある管理対象ファイルも上書きする。
- `pops update-paperops --plan`: versioned upgrade chain を表示する。
- `pops update-paperops --apply-chain`: checkpoint release ごとの `pops` を順に呼び替えて更新する。
- `pops update-harness`: `update-paperops` の互換 alias。
- `pops migrate [path]`: 旧 scaffold に `.pops` 管理情報を追加する計画を表示する。
- `pops feedback`: 上流 `paperops` へ戻す改善フィードバックの下書きを出す。
- `pops links list [path]`: `refs/links.toml` の外部 link を表示する。
- `pops links check [path]`: link registry と local location の対応を検証する。
- `pops scratch archive/reset/restore/list/inspect`: 現在の論文作業層を `_archives/` の split bundle に封印し、同じ repo で1から書き直す。
- `pops version`, `pops --version`: CLI と上流情報を表示する。

## 更新対象

`update-paperops` が扱うのは、下流プロジェクトのハーネス管理面に限る。

- `AGENTS.md`
- `CLAUDE.md`
- `Makefile`
- `TROUBLESHOOTING.md`
- `scripts/`
- `.agents/`
- `.claude/`
- `.github/ISSUE_TEMPLATE/`
- `.github/PULL_REQUEST_TEMPLATE.md`

`README.md`、`manuscript/`、`notes/`、`evidence/`、`claims/`、`review/`、`requests/`、`refs/`、`submission/` はプロジェクト固有内容として自動更新しない。

## Upgrade Chain

後方互換性を最新 `pops` に積み続けないため、scaffold 更新は checkpoint release を跨いで行える。

```sh
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply-chain
uvx --from paper-harness-cli pops update-paperops --target latest --allow-major --apply-chain
```

詳しい保持方針は [upgrade-policy.md](upgrade-policy.md) を参照する。

## Link Registry

共有可能な link intent は `refs/links.toml` に置き、個人環境の絶対パスは ignored な `refs/local/locations.toml` に置く。

```sh
uvx --from paper-harness-cli pops links list --resolve-local
uvx --from paper-harness-cli pops links check
```

`kind = "runops_project"` の link は、runops MCP から publication export、analysis artifact、survey summary、paper request queue を確認する入口として扱う。追加解析や図表要望は `requests/analysis/` に切り出してから runops 側へ渡す。

runops queue へ渡す予定の request は、下流 repo で `make research-request-handoff-check` を実行して確認する。通常は warning のみで、`python scripts/check-research-request-handoff.py --root . --strict` は投稿前や queue handoff の完了判定に使う。

外部 export bundle を図表・表・claim evidence に使う場合は、`refs/imports/` に import state を記録し、`make external-import-check` を実行する。

## Scratch Archives

```sh
uvx --from paper-harness-cli pops scratch archive --label before-rewrite
uvx --from paper-harness-cli pops scratch reset --yes
uvx --from paper-harness-cli pops scratch restore <archive-id> --yes
```

`pops scratch archive` は `manuscript/`、`submission/`、`notes/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/` を `_archives/<id>/archive.zip.partNNNN` に分割保存する。既定の part size は 48 MiB で、GitHub の単一ファイル制限にかからないようにする。

`pops scratch reset --yes` は作業層と `_handoff/` payload を starter 状態に戻す。`_archives/` は残る。通常の AI 執筆では archive 内容を読まず、復元や比較を明示された場合だけ `pops scratch restore <id> --yes` を使う。

## 更新通知

TTY 上で通常コマンドが成功した場合、`pops` は低頻度で PyPI の最新版と `.pops/manifest.toml` の scaffold version を確認する。通知は非阻害で、無効化する場合は `POPS_DISABLE_VERSION_CHECK=1` を設定する。
