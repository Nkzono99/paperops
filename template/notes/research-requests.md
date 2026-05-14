# 追加解析・図表・実験要望

原稿を書きながら発生した runops project や外部データへの要望を記録する。実験実行やジョブ投入はここでは行わず、必要な要望を明確にしてから runops 側の agenda、case、survey、analysis workflow に渡す。

## 要望一覧

| id | link | kind | priority | status | request | target |
|----|------|------|----------|--------|---------|--------|
| RR-0001 | runops-main | analysis_request | medium | open | 結果セクションで必要な比較指標を確認する | `refs/links.toml` の runops link |

## 記録ルール

- `link` は `refs/links.toml` の `id` を使う。
- `kind` は `analysis_request`、`figure_request`、`experiment_request`、`evidence_gap`、`export_request` から選ぶ。
- `status` は `open`、`planned`、`in_progress`、`done`、`dropped` から選ぶ。
- ローカル絶対パスは書かず、必要なら `location_ref` や runops export manifest を参照する。
- 論文本文に使う主張へ昇格したら `notes/claim-evidence-map.md` と `notes/reproducibility.md` に反映する。
