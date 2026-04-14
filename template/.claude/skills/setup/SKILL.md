---
name: setup
description: テンプレートから作成した新しい論文リポジトリの初回セットアップを一括で行う。プロジェクト開始時に使用。
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# setup

テンプレートから作成した新しい論文リポジトリの初回セットアップを実行する。README の「初回使用前」の手順を対話的に一括で行う。

## 前提条件

- `paper-harness-template` の `template/` からコピーまたはテンプレートリポジトリから生成したリポジトリであること。
- プレースホルダーがまだ置き換えられていない状態であること。

## 手順

### 1. セットアップ状態の検出

以下をチェックし、未完了の手順を特定する:

- `README.md` にプレースホルダー（`paper-my-topic`）が残っているか
- `.venv/` が存在するか
- `refs/local/locations.toml` が存在するか
- `tex-env.toml` が存在するか
- `.github/workflows/*.yml` に `YOUR_ORG/paper-harness-template` が残っているか
- `notes/project-brief.md` にプレースホルダーが残っているか
- `manuscript/venue.md` が未記入か
- `notes/contribution-claims.md` がプレースホルダーのままか

既に完了済みの手順はスキップする。全て完了済みの場合はその旨を通知して終了する。

### 2. プロジェクト情報の収集

ユーザーに以下を質問する（一度にまとめて聞く）:

- **リポジトリ名**: 例 `paper-plasma-turbulence`
- **論文トピック**: 1行の説明
- **著者**: 名前（複数可）
- **上流テンプレートリポジトリ**: GitHub のオーナー/リポジトリ名（例 `Nkzono99/paper-harness-template`）
- **投稿先候補**（未定でも可）: ジャーナル名、締切、ページ制限等
- **TeX 環境**（任意）: ユーザー空間 TeX Live のパス、Docker イメージ、またはシステム TeX Live（デフォルト）

### 3. Python 環境の構築

```sh
make venv
```

既に `.venv/` が存在する場合はスキップする。

### 4. ローカル設定ファイルの生成

#### refs/local/locations.toml

`refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーし、ユーザーに以下を案内する:

- パスをプロジェクトのシミュレーション出力や図のソースに合わせて編集すること
- このファイルは `.gitignore` 対象なので個人パスを含めてよいこと

#### tex-env.toml（任意）

ユーザーが TeX 環境情報を提供した場合のみ:

- `tex-env.example.toml` を `tex-env.toml` にコピー
- 提供された TeX Live パスまたは Docker イメージで設定を記入

### 5. GitHub ワークフローの設定

`.github/workflows/*.yml` 内の `YOUR_ORG/paper-harness-template` を、ユーザーが指定した実際のテンプレートリポジトリパスに置換する。

対象ファイル:
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/mirror-check.yml`

### 6. プロジェクトメタデータの記入

収集した情報で以下を更新する:

#### README.md

- `paper-my-topic` をリポジトリ名に置換
- プロジェクトの1行説明を追加

#### notes/project-brief.md

- トピック、目標、著者を記入
- 「この論文が存在する理由」セクションの記入を案内

#### manuscript/venue.md

- 投稿先候補が提供された場合は記入
- 未定の場合はプレースホルダーを維持し、後で記入するよう案内

#### notes/contribution-claims.md

- トピックに基づく貢献主張のドラフトを提案（ユーザーに確認を求める）
- 具体的でない場合はプレースホルダーを維持

### 7. 検証

```sh
make ci
```

エラーがあれば修正を案内する。

## 出力

セットアップ完了後、以下を表示する:

- 実行した手順の一覧
- スキップした手順とその理由
- 手動で後から行う必要がある作業（venue.md の詳細記入、locations.toml のパス設定等）
- 次のステップの提案（「最初のセッションを `/resume-session` で開始してください」等）

## 注意事項

- 既存の内容を上書きしない。プレースホルダーのみ置換する。
- 判断に迷う場合はユーザーに確認する。
- `make venv` の実行には Python 3.11 が必要。見つからない場合はインストールを案内する。
- セットアップの決定を `notes/decision-log.md` に記録する。
