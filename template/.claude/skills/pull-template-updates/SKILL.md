---
name: pull-template-updates
description: 上流の paper-harness-template の変更を下流の論文リポジトリに安全に取り込む。テンプレート更新の適用時に使用。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# pull-template-updates

上流テンプレートリポジトリ（`paper-harness-template`）の変更を、この論文リポジトリに安全に取り込むためのスキル。

## 前提

- 上流リポジトリ: `Nkzono99/paper-harness-template`（`template/` 配下がこのリポジトリのルートに対応）
- 配布リポジトリ: `Nkzono99/paper-harness-scaffold-template`（上流の `template/` がそのままルートに展開される）

## 手順

### 0. 作業前確認

```sh
git rev-parse --show-toplevel
git remote -v
git status --short
```

nested private repo では親 repo と paper repo の変更を混ぜない。Windows の dubious ownership で git が止まる場合は、グローバル設定を変える前に `git -c safe.directory=<repo> -C <repo> ...` の per-command 回避を使う。

### 1. 差分の取得

```sh
# 配布リポジトリの最新を一時ディレクトリにクローン
git clone --depth 1 https://github.com/Nkzono99/paper-harness-scaffold-template.git /tmp/template-latest
```

または上流リポジトリの `template/` を直接参照:

```sh
git clone --depth 1 https://github.com/Nkzono99/paper-harness-template.git /tmp/template-source
# /tmp/template-source/template/ がこのリポジトリのルートに対応
```

### 2. 変更の特定

以下のカテゴリごとに差分を確認する:

| カテゴリ | パス | マージ方針 |
|---------|------|-----------|
| スキル定義 | `.claude/skills/*/SKILL.md` | 上流を優先、ローカルカスタマイズがあれば手動マージ |
| ルール | `.claude/rules/*.md` | 上流を優先 |
| 設定 | `.claude/settings.json` | ローカルの allow/deny カスタマイズを保持しつつマージ |
| スクリプト | `scripts/*.py`, `scripts/*.sh` | 上流を優先、ローカルパッチがあれば手動確認 |
| ワークフロー | `.github/workflows/*.yml` | ローカルのリポジトリパス参照を保持 |
| ドキュメント | `README.md`, `TROUBLESHOOTING.md`, `notes/*.md`, `manuscript/venue.md` | プロジェクト固有内容を保護しつつ手動マージ |
| テンプレート | `CLAUDE.md`, `AGENTS.md` | 上流を優先 |
| Makefile | `Makefile` | 上流を優先、ローカルターゲットがあれば追加 |

### 3. 保護対象（上書きしない）

以下はプロジェクト固有の内容を含むため、上流で上書きしない:

- `notes/project-brief.md`
- `notes/contribution-claims.md`
- `notes/claim-evidence-map.md`
- `notes/reviewer-model.md`
- `notes/ai-use.md`
- `notes/reproducibility.md`
- `notes/handoff.md`
- `notes/todo.md`
- `notes/decision-log.md`
- `manuscript/venue.md`
- `manuscript/mirror/terminology.yml`
- `manuscript/` 配下すべて
- `refs/` 配下すべて
- `notes/` 配下すべて
- `README.md`（プロジェクト固有）
- `.claude/settings.local.json`
- `refs/local/locations.toml`

旧テンプレートから更新する場合のみ、歴史的な `docs/project-brief.md`、`docs/target-venue.md`、`docs/contribution-claims.md`、`docs/terminology-ja-en.md` が残っていないか確認し、現行の `notes/`、`manuscript/venue.md`、`manuscript/mirror/terminology.yml` へ手動で移す。

### 4. マージの実行

1. 差分対象ファイルを一つずつ比較する。
2. 上書き可能なファイルはそのまま置き換える。
3. マージが必要なファイル（`settings.json` など）はローカルカスタマイズを保持しつつ更新する。
4. 変更内容を `notes/decision-log.md` に記録する。

### 5. 検証

```sh
make ci
```

## 出力

- 取り込んだ変更の一覧
- スキップしたファイルの一覧と理由
- 手動確認が必要な項目
- `notes/decision-log.md` への記録
