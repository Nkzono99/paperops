# paperops

`paperops` は、AI エージェントと論文を書くためのプロジェクトハーネスである。

人間が `template/` を手でコピーして使う道具ではない。主導線は `pops` CLI で、Agent が安全に project state を初期化・診断・更新するための execution kernel として扱う。

## 最小セットアップ

新規論文プロジェクト:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

既存プロジェクトを CLI 管理へ寄せる:

```sh
cd paper-my-topic
uvx --from paper-harness-cli pops setup
uvx --from paper-harness-cli pops doctor
```

`template/` はこのリポジトリ内の source of truth であり、`paper-harness-cli` パッケージに bundled scaffold として同梱される。
`pops` は `uvx --from paper-harness-cli pops ...` で実行する。`.venv` は CLI 用ではなく、論文プロジェクトの Python 実行環境が必要な場合に `make venv` で作成する。

## AI 前提の作業ループ

日常運用の主役は、CLI そのものではなく Agent との会話である。

1. 人間が論文トピック、制約、投稿先候補、判断を伝える。
2. Agent が `notes/project-brief.md`、`notes/related-work-map.md`、`notes/result-pattern-map.md`、`notes/claim-evidence-map.md`、`manuscript/venue.md` を整える。
3. `uvx --from paper-harness-cli pops ...` が init / setup / doctor / update-paperops のような決定的操作を担う。
4. 原稿は `manuscript/ja` を中心に進め、必要な block を `manuscript/en` へ同期する。
5. 関連研究を集める場合は `/research-related-work` で調査対象と field framework を作り、raw findings を `refs/research/`、採用文献を `refs/summaries/` と `.bib`、議論を `notes/related-work-map.md` へ分ける。
6. 実験結果や外部ディレクトリが必要なら `refs/links.toml` と `refs/local/locations.toml` で link を解決し、runops project は MCP の read / inspect / plan tool から確認する。
7. 追加解析・図表・実験要望は `notes/research-requests.md` に残し、runops 側の `research/paper_requests.toml` へ handoff する。
8. 構成やハーネスの違和感をまだ修正に固定したくない場合は `/open-paper-scan` で俯瞰し、採用する idea だけ後段の skill へ渡す。
9. 共有前に `make ci`、投稿前に `make pre-submit` でハーネスのゲートを通す。
10. 再利用可能な摩擦は `/feedback-paper-harness` で上流 `paperops` に戻す。

CLI の詳細は [`docs/cli.md`](docs/cli.md) を参照する。

## コア設計思想

- `template/` は個別論文リポジトリに展開される scaffold の source of truth。
- `src/paperops/` は `template/` を展開・診断・更新する薄い CLI。
- `notes/` はセッション継続性、関連研究、主張・証拠、読者モデル、AI 利用ログの共有 memory。作業用ドキュメントは日本語で書く。
- `notes/result-pattern-map.md` は raw result、figure data、analysis artifact を result pattern / evidence packet へ束ね、claim に昇格する前の中間層として扱う。
- `manuscript/ja` と `manuscript/en` は block ID で対応するバイリンガル原稿。
- `refs/` は raw PDF 置き場ではなく、キュレーション済みの参照知識層、関連研究の調査設計、外部 project link 台帳。作業用ドキュメントは日本語で書く。
- `refs/links.toml` は共有可能な link intent を持ち、個人環境の絶対パスは ignored な `refs/local/locations.toml` に分離する。
- `submission/<venue>/` は投稿先公式テンプレートと最終提出用 TeX の隔離スロット。
- `pops update-paperops` はハーネス管理ファイルだけを扱い、下流固有の `manuscript/`、`notes/`、`refs/`、`submission/` を自動上書きしない。

## runops / 外部 project link

論文を書きながら実験結果、図表ソース、外部ノート、データセットを参照する場合、共有ファイルには絶対パスを書かず、`refs/links.toml` に link の意味だけを記録する。実パスは `refs/local/locations.toml` に置き、`pops links list --resolve-local` と `/resolve-local-paths` で解決する。

`kind = "runops_project"` の link は runops MCP 連携の入口である。既存結果は `runops.analysis.artifacts`、`runops.survey.summary`、`runops.publication.exports.list` で確認し、追加要望は `notes/research-requests.md` に記録してから `runops.paper.request.draft` で検証し、人間確認後に runops project の `research/paper_requests.toml` へ渡す。詳細は [`docs/cli.md`](docs/cli.md) と [`docs/skill-catalog.md`](docs/skill-catalog.md) を参照する。

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
- `refs/research/` と `/research-related-work`: 関連研究の outline / field framework / raw findings / 議論を分け、採用する文献だけ `refs/summaries/` と `.bib` へ昇格
- `notes/`: セッション引き継ぎ、result pattern、主張・証拠、読者モデル、AI 利用ログ、継続性の状態管理
- 日本語・英語の原稿をブロックレベルのミラーとして追跡
- `submission/<venue>/`: 投稿先公式テンプレートと最終提出用 TeX の分離
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md`: 公開メタデータ、AI 利用開示、計算環境、図表 provenance の投稿前確認
- `make pre-submit`: `make ci` に加えて引用サマリー、strict mirror freshness、submission slot、スタータープレースホルダー、workflow 参照、公開メタデータ不足を検出
- `make argument-focus-check`: AI 初稿が条件数列挙、防御的 caveat、ローカル実行ログに寄りすぎていないかを advisory に検出
- `/map-result-patterns`: simulation results や figure data を本文の主張へ直接流し込む前に、result pattern / evidence packet として中間層へ束ねる
- `/open-paper-scan`: 改善指示を局所修正へ閉じる前に、原稿・読者体験・執筆ハーネスを発散的に眺める
- `make citation-check`: TeX 本文中の citation key と `.bib` の不整合を早期検出
- `make public-terms-check` / `make claim-evidence-check`: 内部語の公開本文混入と supported claim の evidence 対応を早期検出
- `make mirror-freshness-check` / `make mirror-strict-check` / `make submission-drift-check`: 日英 block の同期鮮度と投稿版への科学的変更戻し忘れを点検
- `make skill-mirror-check`: `.agents/skills/` の共通 skill 実体と `.claude/skills/` の Claude Code wrapper が対応しているかを点検
- `scripts/build-ja.sh` / `scripts/build-en.sh`: `\input` / `\include` / `\includegraphics` / bibliography / style 参照の構造検証を行い、TeX 環境があれば PDF ビルドへ進む
- 下流論文リポジトリ用の Issue フォーム: 原稿レビュー、エビデンス不足、ハーネス摩擦を分けて収集
- テンプレート自体の再利用可能な保守ワークフロー
- プロジェクトローカルの Claude / Codex スキル、フック、運用ルール

## CLI

```sh
uvx --from paper-harness-cli pops init paper-my-topic
uvx --from paper-harness-cli pops setup
uvx --from paper-harness-cli pops doctor
uvx --from paper-harness-cli pops update-paperops --dry-run
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops links list --resolve-local
uvx --from paper-harness-cli pops links check
uvx --from paper-harness-cli pops migrate --apply
uvx --from paper-harness-cli pops feedback
uvx --from paper-harness-cli pops version
```

このコマンド面は `uvx` 経由に一本化する。実装は小さく保ち、既存 skill と Makefile の運用を壊さないことを優先する。
version を跨ぐ scaffold 更新では、`update-paperops --plan` で minor checkpoint ごとの upgrade chain を確認し、必要に応じて `--apply-chain` で exact version の `pops` を順に呼び替える。詳細は [`docs/upgrade-policy.md`](docs/upgrade-policy.md) を参照する。

## PyPI 公開

`paper-harness-cli` は release publish または手動 dispatch で PyPI に公開する。
GitHub Actions の `PyPI 公開` workflow は distribution を build / check し、PyPI Trusted Publishing で `paper-harness-cli` にアップロードする。
PyPI 側では trusted publisher として、この repository、workflow `.github/workflows/publish-pypi.yml`、environment `pypi` を設定しておく。

## 開発と検証

テンプレートは完全な TeX 環境を前提とせず、軽量なローカルチェックを提供する。
`scripts/build-ja.sh` と `scripts/build-en.sh` は `latexmk` が利用可能な場合はコンパイルを行い、そうでなければ `scripts/check-tex-structure.py` による構造検証にフォールバックするため、クリーンなランナーでも CI が執筆ハーネスを実行できる。
開発時のローカルセットアップは、リポジトリローカルの `.venv` 内の Python 3.11 以上である。

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
