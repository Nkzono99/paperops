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
- Pull Request では `Smoke / smoke` を必須チェックとして通す。
- release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。PyPI publish workflow も tag commit が `origin/main` から到達可能な場合だけ公開する。
- 緊急修正でも `main` 直 push は避け、短命 branch と PR を使う。

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
- `git push` はユーザーの明示的な指示なしに実行しない。明示された場合も `main` ではなく topic branch を push する。

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
