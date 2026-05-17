<!-- harnessops により生成; source records が正本 -->
# 手動評価結果: E0003

送信元: `harness-lab/records/eval-cases/E0003-fb0006-built-wheel-scaffold-package-boundary-guard.md`

## スコア

- impact: 4
- mechanism_clarity: 5
- evaluability: 5
- minimality: 3
- regression_risk: 2
- operator_burden: 2
- anti_theater: 5
- maintainability: 4
- privacy_sanitization_risk: 0

## メモ

Priority lane evidence from paperops target repo: template/notes/session-context.generated.md existed before the run; uv build --wheel --out-dir .codex-tmp/priority-20260518-040214-a71d3ef-wheel produced paper_harness_cli-0.2.0-py3-none-any.whl; zip contents included paperops/_data/scaffold/notes/session-context.generated.md, proving release artifact package-data drift is reproducible. Running uvx --from <wheel> pops init .codex-tmp/priority-20260518-040214-a71d3ef-init/paper-demo copied 141 files, excluded 2, and did not create notes/session-context.generated.md, so copy_scaffold currently protects downstream init. The proposed guard is evaluable and worthwhile, but adoption should wait for an implementation that either excludes generated artifacts from the wheel or enforces wheel/install boundary behavior in release smoke.

## 評価ケース

- capability: scaffold package boundary hygiene
- failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries
- source_feedback: FB0006
