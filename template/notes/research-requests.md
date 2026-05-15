# 追加解析・図表・実験要望

原稿を書きながら発生した runops project や外部データへの要望を記録する。実験実行やジョブ投入はここでは行わず、必要な要望を明確にしてから runops 側の agenda、case、survey、analysis workflow に渡す。

## 要望一覧

| id | link | kind | priority | status | runops_id | request | target |
|----|------|------|----------|--------|-----------|---------|--------|
| RR-0001 | runops-main | analysis_request | medium | open | PAPER-REQ-0001 | 結果セクションで必要な比較指標を確認する | `research/paper_requests.toml` |

## 記録ルール

- `link` は `refs/links.toml` の `id` を使う。
- `kind` は `analysis_request`、`figure_request`、`experiment_request`、`evidence_gap`、`export_request` から選ぶ。
- `status` は `open`、`planned`、`in_progress`、`blocked`、`done`、`rejected` から選ぶ。
- ローカル絶対パスは書かず、必要なら `location_ref` や runops export manifest を参照する。
- 論文本文に使う主張へ昇格したら `notes/claim-evidence-map.md` と `notes/reproducibility.md` に反映する。

## runops への handoff

1. `pops links list --resolve-local` で `kind = "runops_project"` の link と実パスを確認する。
2. 既存の結果で足りるかを runops MCP で確認する。図表・解析は `runops.analysis.artifacts` / `runops.survey.summary`、publication export は `runops.publication.exports.list` / `runops.publication.export.inspect` を使う。
3. 追加作業が必要なら、この表の 1 行を runops project の `research/paper_requests.toml` に `[[requests]]` として転記する。
4. 転記後は `runops.paper.requests.list` で queue を確認し、`runops.paper.request.plan` で `research/agenda.md` か `research/proposals/` に戻す導線を確認する。

runops 側に draft/validate MCP がある場合は、手で TOML を書く前にその tool で候補 request を検証する。追加実験や job submit はここからは実行せず、runops 側の明示操作に残す。

```toml
[[requests]]
id = "PAPER-REQ-0001"
type = "analysis_request"
title = "Add comparison metric for the Results section"
paper_id = "paper-my-topic"
paper_context = "Results / Figure 2"
desired_artifact = "table or figure comparing the key metric across the linked survey"
source_link = "refs/links.toml#runops-main"
related_runs = []
related_surveys = []
priority = "medium"
status = "open"
human_gate = true
```
