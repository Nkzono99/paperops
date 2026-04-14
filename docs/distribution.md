# 配布

このリポジトリは論文執筆ハーネスのソースオブトゥルースである。
下流の GitHub テンプレートリポジトリは `template/` から生成される公開アーティファクトである。

## リポジトリの役割

- ソースリポジトリ: `Nkzono99/paper-harness-template`
  - ドキュメント、Issue フォーム、再利用可能ワークフロー、および `template/` 配下のスキャフォールドソースを管理
- 配布リポジトリ: `Nkzono99/paper-harness-scaffold-template`
  - スキャフォールドのみをリポジトリルートに含み、GitHub テンプレートリポジトリとしてマークされている

## 公開モデル

変更はまずここで行う。
`Publish Scaffold` ワークフローが `rsync` で `template/` を配布リポジトリルートに同期する。

## 必要な GitHub Actions 設定

ソースリポジトリで以下を設定する:

- Actions 変数 `PUBLISH_TARGET_REPO`
  - 例: `Nkzono99/paper-harness-scaffold-template`
- Actions シークレット `PUBLISH_TEMPLATE_TOKEN`
  - 配布リポジトリへのプッシュアクセスを持つトークン

## 運用ルール

- 配布リポジトリを手動で編集しない。
- Issue や改善はソースリポジトリに戻す。
- 緊急時に配布リポジトリを直接パッチする必要がある場合、同じ変更を直ちにここにミラーバックする。
