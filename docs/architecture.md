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
- `refs/` 配下の参照知識。外部 project / directory は `refs/links.toml` に共有 metadata だけを置き、ローカル絶対パスは `refs/local/locations.toml` に分離する。raw PDF は `refs/papers/` でローカル保持しても既定では ignore し、共有知識は `refs/summaries/` に集約する
- `notes/` 配下のセッション継続性ノート、主張・証拠台帳、読者モデル、AI 利用ログ
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md` による公開メタデータ・AI 利用ログ・再現性メモ
- `submission/<venue>/` 配下の投稿先公式テンプレートと最終提出用 TeX
- 下流論文リポジトリ用の GitHub Issue フォーム
- プロジェクトローカルの Claude / Codex スキルとフック
- ビルド、TeX 構造、lint、citation key 検証、skill 対応、エクスポート、ノート収集、投稿前 readiness 確認のための軽量スクリプト

## 設計原則

- 原稿リポジトリを自己記述的に保つ。
- アドホックな翻訳に頼らず、日英のドリフトを明示的に追跡する。
- tracked な link registry と ignored な設定ファイルにより、共有可能な外部参照 metadata とローカル絶対パスを分離する。
- 共有・投稿時に、公開メタデータ、再現性、図表 provenance、workflow 設定の未記入を検出する。
- 再利用可能な自動化は各論文リポジトリではなくテンプレートリポジトリに集約する。
- CLI は `template/` を source of truth として展開し、下流プロジェクト固有の原稿・notes・refs を自動上書きしない。
- 下流作成は `pops init` に統一する。
- 検証はインタラクティブセッションと CI の両方で実行できる速度を維持する。
