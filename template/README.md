# paper-my-topic

`paper-harness-template` から構築された個別論文プロジェクトのスターターリポジトリ。

## 初回使用前

1. リポジトリ名を変更し、この README を更新する。
2. `make venv` を実行して Python 3.11 のローカル `.venv` を作成する。
3. `refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーする。
4. `.github/workflows/*.yml` 内のプレースホルダーワークフロー参照を、実際の `paper-harness-template` リポジトリパスに置き換える。
5. `docs/project-brief.md`、`docs/target-venue.md`、`docs/contribution-claims.md` を記入する。

## 基本ワークフロー

1. `resume-session` で開始する。
2. `manuscript/ja/` で執筆または改訂する。
3. 必要なブロックを `manuscript/en/` にミラーする。
4. `notes/` に進捗を記録する。
5. 主要な変更を共有する前に `make ci` を実行する。

ローカルワークフローは `.venv/bin/python` を優先し、それ以外は `python3.11` にフォールバックする。

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、再利用可能な改善はソースリポジトリ `Nkzono99/paper-harness-template` に戻す。
チームが独自のフォーク元を管理していない限り、配布テンプレートリポジトリを主要な Issue トラッカーとして扱わない。

## ディレクトリの概要

- `manuscript/`: バイリンガルソース、共有スタイルアセット、ミラー制御ファイル
- `refs/`: 参照知識、参考文献、抜粋、ローカルパスエイリアス
- `notes/`: セッション継続性と意思決定の追跡
- `.claude/`: プロジェクトローカルの Claude 設定、フック、スキル
- `scripts/`: 軽量な検証・パッケージングヘルパー
