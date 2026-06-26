---
name: update-refs
description: 参考文献と参照知識の整合性を検証する。引用の追加や bib ファイル編集後に使用。
---

# update-refs

参考文献と参照知識を原稿と再同期させる必要がある場合にこのスキルを使用する。

## タスク

1. `manuscript/shared/bib/*.bib` と `_paperops/refs/bib/curated/` をレビューする。
2. 重要な引用論文のサマリーが `_paperops/refs/summaries/` にあるか確認する。
3. `make citation-check` を実行し、原稿内 citation key と `.bib` の不整合をフラグする。
4. キュレーション済みメタデータや利用可能なサマリーが不足している原稿内引用をフラグする。
5. 優先順位に従って次の参照キュレーションタスクを提案する。

## 関連研究を広く集める場合

まだ引用キーが決まっていない関連研究、研究動向、比較対象、反論文献を集める場合は、先に `/research-related-work` を使う。

`update-refs` は、すでに採用する文献や引用キーが見えている段階で、`.bib`、`_paperops/refs/summaries/`、原稿内 citation の整合性を確認するための skill である。

Web、GitHub、動画、RSS、SNS、議論サイトなど source channel 自体の到達経路が未整理な場合は、先に `/source-reach-scan` で `_paperops/notes/source-reach.md` と `_paperops/refs/source-reach/` に raw capture 方針を分ける。

## 原則

- 生の PDF の蓄積よりキュレーション済みサマリーを優先する。
- 原稿に登場した引用キーは安定させる。
- 執筆に影響する未解決の引用問題は `_paperops/notes/open-questions.md` に記録する。
- deep research の raw findings は `_paperops/refs/research/**/results/` に留め、採用する文献だけ `_paperops/refs/summaries/` と `.bib` へ昇格する。
- source reach の raw capture は `_paperops/refs/source-reach/**/raw/` に留め、採用する finding だけ `_paperops/notes/source-reach.md`、`_paperops/refs/summaries/`、`.bib` へ昇格する。

## Codex 実行メモ

- `_paperops/refs/` は生 PDF 置き場ではなく知識層として扱う。
- citation key を安定させ、`manuscript/shared/bib/` と `_paperops/refs/summaries/` の対応を確認する。
- bib や引用を編集したら `make lint-bib` と `make citation-check` を実行する。
