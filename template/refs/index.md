# 参照知識インデックス

## 目的

`refs/` は執筆のための知識層であり、生の論文 PDF 置き場ではない。

## レイアウト

- `links.toml`: paper draft から外部 project / directory への共有 link 台帳。絶対パスは書かず、`location_ref` で `local/` の個人設定へ接続する
- `summaries/`: 再利用に最適化された構造化サマリー（スキルが初回使用時にサブディレクトリを作成）
- `local/`: ignored なマシン固有パスエイリアス
- `papers/`: raw PDF などのローカル保持枠。`.gitkeep` 以外は既定で ignore し、共有知識は `summaries/` に転記する

## 外部 link 台帳

`refs/links.toml` は、この paper draft が参照する runops project、図の編集元、外部ノート、データセットなどを記録する共有台帳である。`kind = "runops_project"` の link は runops MCP や publication export manifest を使う入口として扱い、一般ディレクトリは通常の参照・部分編集の入口として扱う。

個人環境の絶対パスは `refs/local/locations.toml` にだけ書く。原稿、notes、tracked な refs にはローカル絶対パスを混ぜず、必要な provenance は export manifest、artifact index、または `notes/reproducibility.md` に公開可能な形で記録する。

runops project へ追加解析・図表・追加実験の要望を戻す場合は、まず `notes/research-requests.md` に paper 側の文脈を残し、runops 側の `research/paper_requests.toml` に同じ request を転記する。転記後は runops MCP の `runops.paper.requests.list` と `runops.paper.request.plan` で queue と routing を確認する。

## サマリー形式

新しい文献サマリーを作るときは `refs/summaries/summary-template.md` をコピーし、citation key、DOI/URL、引用してよい主張、引用してはいけない主張、人間の検証状態を記録する。

## 必要に応じて作成されるディレクトリ

以下は `/update-refs` や `/import-manuscript` の実行時に必要に応じて自動作成される:

- `papers/`: 論文ファイル（self, related, cited-core）。Git には含めず、必要な内容は `summaries/` に要約する
- `bib/`: インポート済み・キュレーション済みの参考文献レコード
- `excerpts/`: 出典付きの引用・抜粋
