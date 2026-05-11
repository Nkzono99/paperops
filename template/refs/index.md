# 参照知識インデックス

## 目的

`refs/` は執筆のための知識層であり、生の論文 PDF 置き場ではない。

## レイアウト

- `summaries/`: 再利用に最適化された構造化サマリー（スキルが初回使用時にサブディレクトリを作成）
- `local/`: ignored なマシン固有パスエイリアス

## サマリー形式

新しい文献サマリーを作るときは `refs/summaries/summary-template.md` をコピーし、citation key、DOI/URL、引用してよい主張、引用してはいけない主張、人間の検証状態を記録する。

## 必要に応じて作成されるディレクトリ

以下は `/update-refs` や `/import-manuscript` の実行時に必要に応じて自動作成される:

- `papers/`: 論文ファイル（self, related, cited-core）
- `bib/`: インポート済み・キュレーション済みの参考文献レコード
- `excerpts/`: 出典付きの引用・抜粋
