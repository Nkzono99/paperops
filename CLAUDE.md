# CLAUDE.md

ユーザーとは**日本語**でコミュニケーションすること。

これは `paper-harness-template` の**テンプレート管理リポジトリ**である。

## アーキテクチャ

二層構成:

- **ルート層**: テンプレートガバナンス、再利用可能ワークフロー、配布自動化、テンプレート保守スキル
- **`template/` 層**: 個別の `paper-<topic>` リポジトリにコピーされる論文用スキャフォールド

この二つを混同しないこと。ルートレベルのファイルはテンプレート自体を管理し、`template/` は下流ユーザーが受け取る内容を格納する。

## 主要コマンド

```sh
make venv                      # Python 3.11 で .venv を作成
make smoke                     # template/ に対して lint-bib + mirror-check + collect-context を実行
make publish-scaffold-dry-run  # template/ から配布リポジトリへの rsync をプレビュー
```

## 変更ワークフロー

1. 構造化された Issue フォーム（`template-feedback`, `skill-request`, `structure-change`）で Issue を受理する。
2. `/triage-template-feedback` でトリアージする。
3. `/apply-template-improvement` で実装する。
4. `/review-template-regression` でレビューする。
5. マージ前に `make smoke` を実行する。
6. ユーザーに影響する変更ごとに `CHANGELOG.md` を更新する。

変更を反映する前に `docs/change-policy.md` と `docs/triage-rules.md` を確認すること。

## ルール

- `template/AGENTS.md`、`template/CLAUDE.md`、`template/.claude/skills/`、`template/scripts/` は**ユーザー向けインターフェース**として扱う。変更にはマイグレーションノートが必要。
- 構造的な書き換えよりも追加的な変更を優先する。
- 生成されたコンテンツはバージョン管理に含めない。
- 配布リポジトリは**公開先**であり、編集場所ではない。
- `template/` 配下を変更した後は必ず `make smoke` を実行する。
- 長時間セッションでは、コンテキスト使用量が約50%の時点で手動で `/compact` を実行する。

## リポジトリマップ

```
docs/                  architecture, change-policy, triage-rules, skill-catalog, distribution
.claude/skills/        triage-template-feedback, apply-template-improvement, review-template-regression
.github/workflows/     reusable-build, reusable-mirror-check, reusable-release, publish-scaffold
.github/ISSUE_TEMPLATE/ template-feedback, skill-request, structure-change
scripts/               publish-scaffold.sh
template/              下流スキャフォールド一式（template/CLAUDE.md を参照）
```
