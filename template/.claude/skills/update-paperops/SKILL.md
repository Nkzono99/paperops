---
name: update-paperops
description: pops が知らせる paperops 更新、または上流 scaffold 更新を下流論文リポジトリへ安全に取り込む。paperops 更新時に使用。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# update-paperops

上流 `paperops` scaffold の更新を、この論文リポジトリに安全に取り込むためのスキル。

`pops` が paperops 更新通知を出した場合、PyPI の最新配布版を `uvx` で実行し、管理対象ハーネス差分を確認する。

## 前提

- 上流リポジトリ: `Nkzono99/paperops`（`template/` 配下がこのリポジトリのルートに対応）
- 下流プロジェクトは `pops init` または `pops setup` で `.pops/manifest.toml` を持つ。
- GitHub template repository 由来の配布リポジトリは使用しない。
- 旧名 `/pull-template-updates` は互換入口として残す。新規作業では `/update-paperops` を使う。

## 手順

### 0. 作業前確認

```sh
git rev-parse --show-toplevel
git remote -v
git status --short
```

nested private repo では親 repo と paper repo の変更を混ぜない。Windows の dubious ownership で git が止まる場合は、グローバル設定を変える前に `git -c safe.directory=<repo> -C <repo> ...` の per-command 回避を使う。

### 1. pops 実行版の確認

`pops` は project-local `.venv` ではなく、PyPI の配布版を `uvx` から実行する。

```sh
uvx --from paper-harness-cli pops version
```

`uvx` が使えない環境では `uv` の導入を案内し、project-local `.venv` への `pops` インストールで代替しない。

### 2. 差分の取得

```sh
uvx --from paper-harness-cli pops update-paperops --dry-run
```

旧 CLI を使っている場合のみ、互換 alias として `uvx --from paper-harness-cli pops update-harness --dry-run` が使える。

### 3. 変更の特定

以下のカテゴリごとに差分を確認する:

| カテゴリ | パス | マージ方針 |
|---------|------|-----------|
| スキル定義 | `.claude/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md` | 上流を優先、ローカルカスタマイズがあれば手動マージ |
| ルール | `.claude/rules/*.md` | 上流を優先 |
| 設定 | `.claude/settings.json` | ローカルの allow/deny カスタマイズを保持しつつマージ |
| スクリプト | `scripts/*.py`, `scripts/*.sh` | 上流を優先、ローカルパッチがあれば手動確認 |
| ワークフロー | `.github/workflows/*.yml` | ローカルのリポジトリパス参照を保持 |
| テンプレート | `CLAUDE.md`, `AGENTS.md` | 上流を優先、プロジェクト固有追記があれば手動マージ |
| Makefile | `Makefile` | 上流を優先、ローカルターゲットがあれば追加 |

### 4. 保護対象（上書きしない）

以下はプロジェクト固有の内容を含むため、上流で上書きしない:

- `notes/` 配下すべて
- `manuscript/` 配下すべて
- `refs/` 配下すべて
- `submission/` 配下すべて
- `README.md`（プロジェクト固有）
- `.claude/settings.local.json`
- `refs/local/locations.toml`

旧テンプレートから更新する場合のみ、歴史的な `docs/project-brief.md`、`docs/target-venue.md`、`docs/contribution-claims.md`、`docs/terminology-ja-en.md` が残っていないか確認し、現行の `notes/`、`manuscript/venue.md`、`manuscript/mirror/terminology.yml` へ手動で移す。

### 5. マージの実行

1. `uvx --from paper-harness-cli pops update-paperops --apply` で不足している管理対象ファイルを追加する。
2. 変更済み管理対象ファイルは plan を確認し、必要なものだけ手動マージする。
3. 差分を上流に完全置換してよいと判断できる場合のみ `uvx --from paper-harness-cli pops update-paperops --apply --force` を使う。
4. 変更内容を `notes/decision-log.md` に記録する。

### 6. 検証

```sh
uvx --from paper-harness-cli pops doctor
make ci
```

## 出力

- 更新した `pops` version
- 取り込んだ変更の一覧
- スキップしたファイルの一覧と理由
- 手動確認が必要な項目
- `notes/decision-log.md` への記録
