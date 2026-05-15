# アーキテクチャ

このリポジトリはテンプレート保守の関心事と個別論文の執筆関心事を分離している。

## 層構成

### 1. テンプレートリポジトリ層

リポジトリルートは、すべての下流論文リポジトリで共有すべきアセットを管理する:

- 再利用可能な GitHub ワークフロー
- テンプレート改善のための Issue フォーム
- テンプレート保守者向けスキル
- `pops` CLI によるスキャフォールド初期化、診断、ハーネス更新
- 変更履歴とガバナンスドキュメント
- CLI パッケージとして `template/` を bundled scaffold に含めるための配布設定

この層は意図的に小さく安定している。ハーネスを安全に進化させることが役割である。

### 2. 個別論文スキャフォールド層

`template/` は個別原稿リポジトリの完全な構造を含む。
このスキャフォールドには以下が含まれる:

- `ja/` と `en/` に分割された原稿ソース
- `manuscript/mirror/` 配下のミラー制御層と block freshness ledger
- `refs/` 配下の参照知識と外部 link 台帳。raw PDF は `refs/papers/` でローカル保持しても既定では ignore し、共有知識は `refs/summaries/`、外部 project / directory の共有意図は `refs/links.toml` に集約する
- `notes/` 配下のセッション継続性ノート、主張・証拠台帳、読者モデル、AI 利用ログ、追加解析・図表・実験要望
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md` による公開メタデータ・AI 利用ログ・再現性メモ
- `submission/<venue>/` 配下の投稿先公式テンプレートと最終提出用 TeX
- 下流論文リポジトリ用の GitHub Issue フォーム
- プロジェクトローカルの Claude / Codex スキルとフック
- ビルド、TeX 構造、lint、citation key 検証、skill 対応、エクスポート、ノート収集、投稿前 readiness 確認のための軽量スクリプト

## 設計原則

- 原稿リポジトリを自己記述的に保つ。
- アドホックな翻訳に頼らず、日英のドリフトを明示的に追跡する。
- エイリアスと ignored な設定ファイルによりローカルパスを保存する。
- paper draft から runops project や一般ディレクトリを参照する場合、共有 link metadata と個人環境の絶対パスを分離する。
- runops project link ではローカルパス直読みより MCP の read / inspect / plan tool を優先し、追加要望は `runops.paper.request.draft` で検証してから handoff する。
- 共有・投稿時に、公開メタデータ、再現性、図表 provenance、workflow 設定の未記入を検出する。
- 再利用可能な自動化は各論文リポジトリではなくテンプレートリポジトリに集約する。
- CLI は `template/` を source of truth として展開し、下流プロジェクト固有の原稿・notes・refs を自動上書きしない。
- 下流作成は `pops init` に統一する。
- 検証はインタラクティブセッションと CI の両方で実行できる速度を維持する。

## 外部 project link の情報境界

`refs/links.toml` は下流リポジトリで共有できる link の意味だけを持つ。実パス、ホスト名、ユーザー固有の配置は ignored な `refs/local/locations.toml` に置く。これにより、paper draft は runops project や一般ディレクトリを参照できるが、リポジトリには移植不能な絶対パスを混ぜない。

runops project の成果物は、まず publication export、analysis artifact、survey summary などの structured output を MCP 経由で読む。paper 側で追加解析・図表・実験要望が発生した場合は、`notes/research-requests.md` で paper 文脈を残し、runops 側の `research/paper_requests.toml` へ request として戻す。
