# 参照知識インデックス

## 目的

`refs/` は執筆のための知識層であり、生の論文 PDF 置き場ではない。

## レイアウト

- `links.toml`: paper draft から外部 project / directory への共有 link 台帳。絶対パスは書かず、`location_ref` で `local/` の個人設定へ接続する
- `summaries/`: 再利用に最適化された構造化サマリー（スキルが初回使用時にサブディレクトリを作成）
- `research/`: 関連研究を広く集めるための調査設計、field framework、議論前の一時成果物の置き場
- `source-reach/`: 外部 Web、GitHub、動画、RSS、SNS などの到達経路と raw capture の一時領域
- `links.toml`: 外部 project / directory の共有可能な metadata registry。絶対パスは含めず、`refs/local/locations.toml` の alias を参照する
- `links.md`: link registry の schema と運用メモ
- `imports/`: 外部 export bundle の source index、integrity manifest、source commit、claim role の import state
- `local/`: ignored なマシン固有パスエイリアス
- `papers/`: raw PDF などのローカル保持枠。`.gitkeep` 以外は既定で ignore し、共有知識は `summaries/` に転記する

## 外部 link 台帳

`refs/links.toml` は、この paper draft が参照する runops project、図の編集元、外部ノート、データセットなどを記録する共有台帳である。`kind = "runops_project"` の link は runops MCP や publication export manifest を使う入口として扱い、一般ディレクトリは通常の参照・部分編集の入口として扱う。

個人環境の絶対パスは `refs/local/locations.toml` にだけ書く。原稿、notes、tracked な refs にはローカル絶対パスを混ぜず、必要な provenance は export manifest、artifact index、または `notes/reproducibility.md` に公開可能な形で記録する。

外部 bundle の図表や CSV を使う場合は、`refs/imports/README.md` に従って import state を記録する。

runops project へ追加解析・図表・追加実験の要望を戻す場合は、まず `requests/analysis/` に paper 側の文脈を残し、`notes/views/research-requests.md` で俯瞰する。runops MCP の `runops.paper.request.draft` で候補 request を検証する。人間が確認した snippet だけを runops 側の `research/paper_requests.toml` に転記し、転記後は `runops.paper.requests.list` と `runops.paper.request.plan` で queue と routing を確認する。

## 関連研究の探索

関連研究、研究動向、比較対象、反論文献を広く集める場合は `/research-related-work` を使う。調査対象と field framework は `refs/research/<topic-slug>/` に置き、raw findings は既定で Git 管理しない。採用する文献だけを `refs/summaries/`、`manuscript/shared/bib/references.bib`、`notes/related-work-map.md` へ昇格する。

## 外部ソース到達

Web、GitHub、動画、RSS、SNS、議論サイトなどを調べる場合は `/source-reach-scan` で source channel、preferred route、fallback、credential need、raw capture policy を決める。raw capture は `refs/source-reach/**/raw/` に置いても既定では Git 管理しない。論文で使う確認済み finding だけを `notes/source-reach.md`、`notes/related-work-map.md`、`refs/summaries/`、`notes/reproducibility.md` へ昇格する。

## サマリー形式

新しい文献サマリーを作るときは `refs/summaries/summary-template.md` をコピーし、citation key、DOI/URL、引用してよい主張、引用してはいけない主張、人間の検証状態を記録する。

## 必要に応じて作成されるディレクトリ

以下は `/update-refs` や `/import-manuscript` の実行時に必要に応じて自動作成される:

- `papers/`: 論文ファイル（self, related, cited-core）。Git には含めず、必要な内容は `summaries/` に要約する
- `bib/`: インポート済み・キュレーション済みの参考文献レコード
- `excerpts/`: 出典付きの引用・抜粋
