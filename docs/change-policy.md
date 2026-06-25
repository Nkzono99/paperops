# 変更ポリシー

## 目標

テンプレートの変更は、複数の論文リポジトリを改善し、後方互換性を意識し、容易に導入できるものであるべきである。

## 判断ルール

1. 構造的な書き換えよりも追加的な変更を優先する。
2. `template/AGENTS.md`、`template/CLAUDE.md`、`template/contracts/`、`template/.claude/skills/`、`template/.agents/skills/`、`template/scripts/` はユーザー向けインターフェースとして扱う。
3. 下流リポジトリにファイル名変更、ディレクトリ移動、フックの書き換えを強いる変更には、文書化されたマイグレーションノートが必要。
4. チェックイン済みのスターターアーティファクトでない限り、生成されたコンテンツをバージョン管理に含めない。
5. 下流プロジェクトの作成導線は `pops init` に統一する。

## リリース要件

- 一人開発では `main` へ直接取り込んでよい。
- `make smoke` は必須 gate ではなく、リスクの高い変更や公開前確認で必要に応じて通す。
- ユーザーに影響する改善ごとに `CHANGELOG.md` を更新する。
- 変更が下流のセットアップに影響する場合、`README.md`、`docs/cli.md`、および `template/` 内の該当ファイルを更新する。
- 判断に迷う場合は、まず `template-feedback` Issue を作成し、変更を反映する前にスコープをトリアージする。
- release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。
