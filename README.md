# paper-harness-template

AI 支援による論文執筆のための再利用可能なハーネス。

このリポジトリは `SPEC.md` に記述された `paper-template` 側として構成されている。
二つの層で構成される:

- テンプレート自体を管理するためのリポジトリレベルのアセット
- [`template/`](/home/b/b36291/large1/Github/paper-harness-template/template) 配下の個別論文用スキャフォールド一式

## リポジトリ構成

- [`.github/workflows/`](/home/b/b36291/large1/Github/paper-harness-template/.github/workflows): 下流の論文リポジトリから呼び出し可能な再利用可能 GitHub Actions ワークフロー
- [`.github/ISSUE_TEMPLATE/`](/home/b/b36291/large1/Github/paper-harness-template/.github/ISSUE_TEMPLATE): フィードバック、スキルリクエスト、構造変更用の構造化 Issue フォーム
- [`.claude/skills/`](/home/b/b36291/large1/Github/paper-harness-template/.claude/skills): テンプレートトリアージ・保守用スキル
- [`template/.agents/skills/`](/home/b/b36291/large1/Github/paper-harness-template/template/.agents/skills): Codex 用の下流執筆スキル互換入口
- [`docs/`](/home/b/b36291/large1/Github/paper-harness-template/docs): テンプレートアーキテクチャ、変更ポリシー、トリアージルール
- [`template/`](/home/b/b36291/large1/Github/paper-harness-template/template): 個別の `paper-<topic>` リポジトリにコピー可能なスキャフォールド
- [`docs/distribution.md`](/home/b/b36291/large1/Github/paper-harness-template/docs/distribution.md): `template/` を別の GitHub テンプレートリポジトリに同期する配布モデル

## クイックスタート

1. `template/` を別の配布リポジトリに公開するか、`paper-my-topic/` などの新しいリポジトリに手動でコピーする。
2. `make venv` を実行して Python 3.11 のローカル `.venv` を作成する。
3. リポジトリ名を変更し、以下のスターターファイルを更新する:
   - `README.md`
   - `notes/project-brief.md`
   - `manuscript/venue.md`
   - `notes/contribution-claims.md`
   - `refs/local/locations.example.toml` から `refs/local/locations.toml` を作成し、ローカルパスはユーザー自身で記入
4. まず `manuscript/ja` に原稿を書き、必要なセクションを `manuscript/en` に同期する。
5. 論文リポジトリで `make ci` を実行して、参考文献の lint、ミラーカバレッジの検証、ビルドハーネスの動作確認を行う。

## スキャフォールドが最適化するもの

- `refs/`: 生の PDF 置き場ではなく共有知識層として活用
- `notes/`: セッション引き継ぎ、主張・証拠、読者モデル、AI 利用ログ、継続性の状態管理
- 日本語・英語の原稿をブロックレベルのミラーとして追跡
- `submission/<venue>/`: 投稿先公式テンプレートと最終提出用 TeX の分離
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md`: 公開メタデータ、AI 利用開示、計算環境、図表 provenance の投稿前確認
- `make pre-submit`: `make ci` に加えてスタータープレースホルダー、workflow 参照、公開メタデータ不足を検出
- `make citation-check`: TeX 本文中の citation key と `.bib` の不整合を早期検出
- `make public-terms-check` / `make claim-evidence-check`: 内部語の公開本文混入と supported claim の evidence 対応を早期検出
- `make mirror-freshness-check` / `make submission-drift-check`: 日英 block の同期鮮度と投稿版への科学的変更戻し忘れを点検
- 下流論文リポジトリ用の Issue フォーム: 原稿レビュー、エビデンス不足、ハーネス摩擦を分けて収集
- テンプレート自体の再利用可能な保守ワークフロー
- プロジェクトローカルの Claude / Codex スキル、フック、運用ルール

## 配布

GitHub の `Use this template` フローを使いたい場合、このリポジトリをソースオブトゥルースとして維持し、`template/` をスキャフォールドのみを含む別のリポジトリに公開する。
このリポジトリには、その同期パス用の [`scripts/publish-scaffold.sh`](/home/b/b36291/large1/Github/paper-harness-template/scripts/publish-scaffold.sh) と [`.github/workflows/publish-scaffold.yml`](/home/b/b36291/large1/Github/paper-harness-template/.github/workflows/publish-scaffold.yml) が含まれている。

## 検証モデル

テンプレートは完全な TeX 環境を前提とせず、軽量なローカルチェックを提供する。
`scripts/build-ja.sh` と `scripts/build-en.sh` は `latexmk` が利用可能な場合はコンパイルを行い、そうでなければ構造検証にフォールバックするため、クリーンなランナーでも CI が執筆ハーネスを実行できる。
想定されるローカルセットアップは、リポジトリローカルの `.venv` 内の `python3.11` である。

## 上流リファレンス

フックと設定のレイアウトは Anthropic の Claude Code ドキュメントのプロジェクト設定とフックに準拠しており、GitHub 自動化ファイルは GitHub の再利用可能ワークフローと Issue フォームのドキュメントに準拠している:

- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations
- https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
