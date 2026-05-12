---
name: feedback-paper-harness
description: 再利用可能な改善を上流の paperops にフィードバックする。プロジェクト固有でない摩擦がある場合に使用。
allowed-tools: Read, Glob, Grep
---

# feedback-paper-harness

繰り返しの問題を上流のペーパーハーネスソースリポジトリで修正すべき場合にこのスキルを使用する。

## デフォルトの上流ターゲット

- ソースリポジトリ: `Nkzono99/paperops`
- チームがハーネスをフォークし独自のソースリポジトリを管理している場合は、そのフォークを使用する。
- GitHub template repository や配布専用リポジトリではなく、`pops` CLI と `template/` の source repository へ戻す。

## 収集する情報

- 観測されたペインポイント
- このリポジトリでの再現方法
- 修正が再利用可能である理由
- 提案する実装先
- マイグレーションまたは互換性の懸念事項

## 出力

`pops feedback` または `Nkzono99/paperops` の上流 `template-feedback` Issue フォームに貼り付け可能な形式でフィードバックを記述する。

## スコープガード

投稿先固有の表現、論文固有の科学的選択、個人的なローカルパス慣習はエスカレートしない。
