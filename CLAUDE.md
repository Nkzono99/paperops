# CLAUDE.md

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

- このリポジトリは `.harnessops/project.toml` 上では `target-repository` で、HOPS overlay は `harness-lab/` を使う。
- HarnessOps 管理ファイルは直接組み替えず、確認は `uvx --from harnessops hops doctor --check-overlay --check-records`、更新は `uvx --refresh-package harnessops --from harnessops hops update-harness` を使う。
- GitHub Flow 作業を HOPS に委譲する場合は `.agents/skills/hops-github-flow/SKILL.md` と `uvx --from harnessops hops github-flow ...` を使う。
- repo-local skill の更新や bridge 再展開が必要な場合は `.agents/skills/hops-update-harness/SKILL.md` の手順に従う。

## 変更ワークフロー

1. 構造化された Issue フォーム（`template-feedback`, `skill-request`, `structure-change`）で Issue を受理する。
2. `/triage-template-feedback` でトリアージする。
3. `/apply-template-improvement` で実装する。
4. `/review-template-regression` でレビューする。
5. マージ前に `make smoke` を実行する。
6. ユーザーに影響する変更ごとに `CHANGELOG.md` を更新する。

変更を反映する前に `docs/change-policy.md` と `docs/triage-rules.md` を確認すること。

## GitHub Flow

- `main` への直接 push は禁止。すべての変更は `codex/<topic>` などの topic branch から Pull Request 経由で取り込む。
- ユーザーが「mergeして」「pushして」と依頼した場合も、明示的に `main` 直 push を求めていない限り、topic branch を push して Pull Request を作成し、GitHub 上で merge する。
- ローカル `main` に誤って commit や merge を作った場合も、`origin/main` へ直接 push せず、その commit を topic branch から Pull Request に出し、merge 後にローカル `main` を `origin/main` へ fast-forward する。
- Pull Request では `Smoke / smoke` を必須チェックとして通す。
- release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。PyPI publish workflow も tag commit が `origin/main` から到達可能な場合だけ公開する。
- 緊急修正でも `main` 直 push は避け、短命 branch と PR を使う。

## ルール

- `template/AGENTS.md`、`template/CLAUDE.md`、`template/.claude/skills/`、`template/.agents/skills/`、`template/scripts/` は**ユーザー向けインターフェース**として扱う。変更にはマイグレーションノートが必要。
- 構造的な書き換えよりも追加的な変更を優先する。
- 生成されたコンテンツはバージョン管理に含めない。
- 下流作成は `pops init` に統一する。
- `template/` 配下を変更した後は必ず `make smoke` を実行する。
- 長時間セッションでは、コンテキスト使用量が約50%の時点で手動で `/compact` を実行する。

## Git コミットルール

- 意味のある作業単位ごとにコミットする。大量の変更を一つのコミットにまとめない。
- コミットメッセージは日本語で、変更の「なぜ」を記述する。
- `git push` はユーザーの明示的な指示なしに実行しない。明示された場合も `main` ではなく topic branch を push する。

## リポジトリマップ

```
docs/                  architecture, change-policy, triage-rules, skill-catalog, distribution
.claude/skills/        triage-template-feedback, apply-template-improvement, review-template-regression
template/.agents/      Codex 用の下流執筆スキル互換入口
.github/workflows/     reusable-build, reusable-mirror-check, reusable-release, publish-pypi
.github/ISSUE_TEMPLATE/ template-feedback, skill-request, structure-change
src/paperops/          pops CLI
scripts/               smoke helpers
template/              下流スキャフォールド一式（template/CLAUDE.md を参照）
```
