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
| ドキュメント | `docs/agent-operating-rules.md`, `docs/writing-policy.md` | 上流を優先 |
| テンプレート | `CLAUDE.md`, `AGENTS.md` | 上流を優先 |
| Makefile | `Makefile` | 上流を優先、ローカルターゲットがあれば追加 |

### 3. 保護対象（上書きしない）

以下はプロジェクト固有の内容を含むため、上流で上書きしない:

- `docs/project-brief.md`
- `docs/target-venue.md`
- `docs/contribution-claims.md`
- `docs/terminology-ja-en.md`
- `manuscript/` 配下すべて
- `refs/` 配下すべて
- `notes/` 配下すべて
- `README.md`（プロジェクト固有）
- `.claude/settings.local.json`
- `refs/local/locations.toml`

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
