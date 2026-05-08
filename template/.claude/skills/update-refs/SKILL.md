---
name: update-refs
description: 参考文献と参照知識の整合性を検証する。引用の追加や bib ファイル編集後に使用。
allowed-tools: Read, Edit, Write, Glob, Grep
---

# update-refs

参考文献と参照知識を原稿と再同期させる必要がある場合にこのスキルを使用する。

## タスク

1. `manuscript/shared/bib/*.bib` と `refs/bib/curated/` をレビューする。
2. 重要な引用論文のサマリーが `refs/summaries/` にあるか確認する。
3. `make citation-check` を実行し、原稿内 citation key と `.bib` の不整合をフラグする。
4. キュレーション済みメタデータや利用可能なサマリーが不足している原稿内引用をフラグする。
5. 優先順位に従って次の参照キュレーションタスクを提案する。

## 原則

- 生の PDF の蓄積よりキュレーション済みサマリーを優先する。
- 原稿に登場した引用キーは安定させる。
- 執筆に影響する未解決の引用問題は `notes/open-questions.md` に記録する。
