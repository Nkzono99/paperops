# paper-my-topic

`paper-harness-template` から構築された個別論文プロジェクトのスターターリポジトリ。

## 初回使用前

`/setup` スキルで以下の手順を一括実行できる:

1. リポジトリ名を変更し、この README を更新する。
2. `make venv` を実行して Python 3.11 のローカル `.venv` を作成する。
3. `refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーする。
4. `tex-env.example.toml` を `tex-env.toml` にコピーし、TeX 環境を設定する（任意）。
5. `.github/workflows/*.yml` 内のプレースホルダーワークフロー参照を、実際の `paper-harness-template` リポジトリパスに置き換える。
6. `notes/project-brief.md`、`manuscript/venue.md`、`notes/contribution-claims.md` を記入する。

## 基本ワークフロー

1. `resume-session` で開始する。
2. `manuscript/ja/` で執筆または改訂する。
3. 必要なブロックを `manuscript/en/` にミラーする。
4. `notes/` に進捗を記録する。
5. 主要な変更を共有する前に `make ci` を実行する。

既存原稿がある場合は `/import-manuscript` でインポートできる。

ローカルワークフローは `.venv/bin/python` を優先し、それ以外は `python3.11` にフォールバックする。

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、再利用可能な改善はソースリポジトリ `Nkzono99/paper-harness-template` に戻す。

## ディレクトリの概要

- `manuscript/`: バイリンガルソース、共有アセット、ミラー制御、投稿先情報
- `refs/`: 参照知識、サマリー、ローカルパスエイリアス（papers, bib 等はスキルが必要時に作成）
- `notes/`: プロジェクト概要、貢献主張、引き継ぎ、意思決定の追跡
- `.claude/`: プロジェクトローカルの設定、スキル、ルール、フック
- `scripts/`: 軽量な検証・パッケージングヘルパー
