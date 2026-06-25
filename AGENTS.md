# AGENTS.md

ユーザーとは**日本語**でコミュニケーションすること。

これは `paperops` の**テンプレート管理リポジトリ**である。

## アーキテクチャ

二層構成:

- **ルート層**: テンプレートガバナンス、再利用可能ワークフロー、`pops` CLI、テンプレート保守スキル
- **`template/` 層**: 個別の `paper-<topic>` リポジトリにコピーされる論文用スキャフォールド

この二つを混同しないこと。ルートレベルのファイルはテンプレート自体を管理し、`template/` は下流ユーザーが受け取る内容を格納する。

## 主要コマンド

```sh
make venv                      # Python 3.11 以上で .venv を作成
make smoke                     # template/ に対して lint-bib + citation-check + mirror-check + collect-context + readiness-check を実行
make cli-smoke                 # pops CLI の最小 smoke test を実行
```

## HarnessOps

- このリポジトリは `.harnessops/project.toml` 上では `target-repository` で、HOPS overlay は `storage = "local"` の `harness-lab/` を使う。正本は `local_id = "paper-harness-template"` で解決される `~/.harnessops/projects/paper-harness-template/` 側に置く。
- 下流 project repo に HOPS をリンクする場合も、`uvx --from harnessops hops project link --profile paper-harness-project` を使い、`harness-feedback/` を repo 外の local state に置く。
- HarnessOps 管理ファイルは直接組み替えず、確認は `uvx --from harnessops hops doctor --check-overlay --check-records`、local state 更新は `uvx --refresh-package harnessops --from harnessops hops update-harness` を使う。
- HOPS 関連 skill は HarnessOps plugin から参照し、この repo には vendor しない。

## 変更ワークフロー

1. 構造化された Issue フォーム（`template-feedback`, `skill-request`, `structure-change`）で Issue を受理する。
2. `/triage-template-feedback` でトリアージする。
3. `/apply-template-improvement` で実装する。
4. `/review-template-regression` でレビューする。
5. マージ前に `make smoke` を実行する。
6. ユーザーに影響する変更ごとに `CHANGELOG.md` を更新する。

変更を反映する前に `docs/change-policy.md` と `docs/triage-rules.md` を確認すること。

## Git 運用

- 一人開発のため、通常の変更は `main` で直接進めてよい。
- ユーザーが「mergeして」「pushして」と依頼した場合は、特に指定がなければ現在の作業を `main` に取り込んで push する。
- `make smoke` は必須 gate ではない。リスクの高い変更や公開前確認で必要な場合に使う。
- release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。PyPI publish workflow も tag commit が `origin/main` から到達可能な場合だけ公開する。

## ルール

- `template/AGENTS.md`、`template/CLAUDE.md`、`template/.agents/skills/`、`template/.claude/skills/`、`template/scripts/` は**ユーザー向けインターフェース**として扱う。変更にはマイグレーションノートが必要。
- 構造的な書き換えよりも追加的な変更を優先する。
- 生成されたコンテンツはバージョン管理に含めない。
- 下流作成は `pops init` に統一する。
- `template/` 配下を変更した後は必ず `make smoke` を実行する。
- 長時間セッションでは、コンテキスト使用量が約50%の時点で手動で `/compact` を実行する。

## Git コミットルール

- 意味のある作業単位ごとにコミットする。大量の変更を一つのコミットにまとめない。
- コミットメッセージは日本語で、変更の「なぜ」を記述する。
- `git push` はユーザーの明示的な指示なしに実行しない。明示された場合は、必要に応じて `main` へ直接 push してよい。

## リポジトリマップ

```
docs/                  architecture, change-policy, triage-rules, skill-catalog, distribution
.Codex/skills/        triage-template-feedback, apply-template-improvement, review-template-regression
.github/workflows/     reusable-build, reusable-mirror-check, reusable-release, publish-pypi
.github/ISSUE_TEMPLATE/ template-feedback, skill-request, structure-change
src/paperops/          pops CLI
scripts/               smoke helpers
template/              下流スキャフォールド一式（template/AGENTS.md を参照）
```
