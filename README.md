# paperops

`paperops` は、AI エージェントと論文を書くためのプロジェクトハーネスである。

人間が `template/` を手でコピーして使う道具ではない。主導線は `pops` CLI で、Agent が安全に project state を初期化・診断・更新するための execution kernel として扱う。

## 最小セットアップ

新規論文プロジェクト:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
.venv\Scripts\Activate.ps1  # Windows / PowerShell
# source .venv/bin/activate  # macOS / Linux
pops doctor
```

既存プロジェクトを CLI 管理へ寄せる:

```sh
cd paper-my-topic
uvx --from paper-harness-cli pops setup
.venv\Scripts\Activate.ps1  # Windows / PowerShell
# source .venv/bin/activate  # macOS / Linux
pops doctor
```

`template/` はこのリポジトリ内の source of truth であり、`paper-harness-cli` パッケージに bundled scaffold として同梱される。
`pops init` / `pops setup` はプロジェクトローカルの `.venv` を作成し、その中に `paper-harness-cli` をインストールする。以後の `pops` は、この `.venv` を activate して実行する想定である。

## AI 前提の作業ループ

日常運用の主役は、CLI そのものではなく Agent との会話である。

1. 人間が論文トピック、制約、投稿先候補、判断を伝える。
2. Agent が `notes/project-brief.md`、`notes/claim-evidence-map.md`、`manuscript/venue.md` を整える。
3. `pops` が init / setup / doctor / update-paperops のような決定的操作を担う。
4. 原稿は `manuscript/ja` を中心に進め、必要な block を `manuscript/en` へ同期する。
5. 共有前に `make ci`、投稿前に `make pre-submit` でハーネスのゲートを通す。
6. 再利用可能な摩擦は `/feedback-paper-harness` で上流 `paperops` に戻す。

CLI の詳細は [`docs/cli.md`](docs/cli.md) を参照する。

## コア設計思想

- `template/` は個別論文リポジトリに展開される scaffold の source of truth。
- `src/paperops/` は `template/` を展開・診断・更新する薄い CLI。
- `notes/` はセッション継続性、主張・証拠、読者モデル、AI 利用ログの共有 memory。
- `manuscript/ja` と `manuscript/en` は block ID で対応するバイリンガル原稿。
- `refs/` は raw PDF 置き場ではなく、キュレーション済みの参照知識層。
- `submission/<venue>/` は投稿先公式テンプレートと最終提出用 TeX の隔離スロット。
- `pops update-paperops` はハーネス管理ファイルだけを扱い、下流固有の `manuscript/`、`notes/`、`refs/`、`submission/` を自動上書きしない。

## リポジトリ構成

- `src/paperops/`: `pops` CLI
- `template/`: 論文プロジェクトに展開される scaffold
- `.github/workflows/`: 下流論文リポジトリから呼び出し可能な再利用可能 GitHub Actions workflow
- `.github/ISSUE_TEMPLATE/`: テンプレート改善、スキル要求、構造変更の Issue フォーム
- `.claude/skills/`, `.agents/skills/`: テンプレート保守用 skill
- `docs/`: アーキテクチャ、変更ポリシー、トリアージルール、CLI と配布方針
- `tests/`: `pops` CLI の最小 smoke tests

## スキャフォールドが最適化するもの

- `refs/`: 生の PDF 置き場ではなく共有知識層として活用
- `notes/`: セッション引き継ぎ、主張・証拠、読者モデル、AI 利用ログ、継続性の状態管理
- 日本語・英語の原稿をブロックレベルのミラーとして追跡
- `submission/<venue>/`: 投稿先公式テンプレートと最終提出用 TeX の分離
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md`: 公開メタデータ、AI 利用開示、計算環境、図表 provenance の投稿前確認
- `make pre-submit`: `make ci` に加えて引用サマリー、submission slot、スタータープレースホルダー、workflow 参照、公開メタデータ不足を検出
- `make citation-check`: TeX 本文中の citation key と `.bib` の不整合を早期検出
- `make public-terms-check` / `make claim-evidence-check`: 内部語の公開本文混入と supported claim の evidence 対応を早期検出
- `make mirror-freshness-check` / `make submission-drift-check`: 日英 block の同期鮮度と投稿版への科学的変更戻し忘れを点検
- `make skill-mirror-check`: `.agents/skills/` が `.claude/skills/` の同名 source of truth を参照しているかを点検
- `scripts/build-ja.sh` / `scripts/build-en.sh`: `\input` / `\include` / `\includegraphics` / bibliography / style 参照の構造検証を行い、TeX 環境があれば PDF ビルドへ進む
- 下流論文リポジトリ用の Issue フォーム: 原稿レビュー、エビデンス不足、ハーネス摩擦を分けて収集
- テンプレート自体の再利用可能な保守ワークフロー
- プロジェクトローカルの Claude / Codex スキル、フック、運用ルール

## CLI

```sh
pops init paper-my-topic
pops setup
pops doctor
pops update-paperops --dry-run
pops migrate --apply
pops feedback
pops version
```

このコマンド面は将来の CLI 標準化前の最小形である。標準化までは、実装を小さく保ち、既存 skill と Makefile の運用を壊さないことを優先する。

## PyPI 公開

`paper-harness-cli` は release publish または手動 dispatch で PyPI に公開する。
GitHub Actions の `PyPI 公開` workflow は distribution を build / check し、PyPI Trusted Publishing で `paper-harness-cli` にアップロードする。
PyPI 側では trusted publisher として、この repository、workflow `.github/workflows/publish-pypi.yml`、environment `pypi` を設定しておく。

## 開発と検証

テンプレートは完全な TeX 環境を前提とせず、軽量なローカルチェックを提供する。
`scripts/build-ja.sh` と `scripts/build-en.sh` は `latexmk` が利用可能な場合はコンパイルを行い、そうでなければ `scripts/check-tex-structure.py` による構造検証にフォールバックするため、クリーンなランナーでも CI が執筆ハーネスを実行できる。
想定されるローカルセットアップは、リポジトリローカルの `.venv` 内の Python 3.11 以上である。

```sh
make venv
make smoke
python -m pip wheel . --no-deps -w .codex-tmp/wheelhouse
```

## 上流リファレンス

フックと設定のレイアウトは Anthropic の Claude Code ドキュメントのプロジェクト設定とフックに準拠しており、GitHub 自動化ファイルは GitHub の再利用可能ワークフローと Issue フォームのドキュメントに準拠している:

- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations
- https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
