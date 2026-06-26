# pops CLI

`pops` は、`paperops` の scaffold を初期化・診断・更新する薄い CLI である。研究判断や原稿編集は Agent / skill が担当し、`pops` は決定的なファイル操作を担当する。

## 実行方法

標準実行は常に `uvx` 経由にする。

```sh
uvx --from paper-harness-cli pops version
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

`pops init` / `pops setup` は `.pops/manifest.toml` を作成するが、CLI 用の project-local `.venv` は作らない。`.venv` は論文プロジェクト用の Python 環境が必要な場合に `make venv` で作る。

下流の Makefile は、確認を三つの profile に分ける。

- `make ci`: 構造、引用、mirror、公開語彙、カード層、link、build fallback など、壊れていると作業を続けにくい項目を確認する。
- `make audit`: argument focus、concept-term compression、content-first intent、main-text figure reference、figure obligation、claim evidence、外部 bundle import state、research request handoff、submission drift など、執筆品質や handoff drift の advisory checks を確認する。
- `make section-depth-check`: Results / Discussion が `manuscript/writing-profile.yml` の `section_depth` floor を大きく下回っていないか advisory に確認する。JA は `ja_chars`、EN は `en_words` として数える。
- `make finish-manuscript-check`: STRUCTURE_ACCEPTED 前に `/goal` を完了扱いしないための content-first finish gate。`make pre-submit` とは別に、原稿本文 blocker と Results / Discussion の section-depth blocker が閉じているかを確認する。
- `make pre-submit`: `ci` と `audit`、`finish-manuscript-check` に加え、concept term、figure reference、figure obligation、research request handoff、external import、readiness を投稿前 profile として厳しめに確認する。

## コマンド一覧

- `pops init [path]`: bundled scaffold から新規論文リポジトリを作る。
- `pops setup [path]`: 既存リポジトリを `.pops` 管理に採用する。
- `pops setup <git-url> --path <dir>`: clone してから setup する。
- `pops doctor [path]`: 構造、`.pops`、Git / make、workflow placeholder、link registry を確認する。
- `pops update-paperops`: 管理対象ハーネスファイルの更新計画を表示する。
- `pops update-paperops --apply`: 不足している管理対象ファイルだけ追加する。
- `pops update-paperops --apply --force`: 差分がある管理対象ファイルも上書きする。
- `pops update-paperops --plan`: versioned upgrade chain を表示する。
- `pops update-paperops --apply-chain`: checkpoint release ごとの `pops` を順に呼び替えて更新する。
- `pops update-harness`: `update-paperops` の互換 alias。
- `pops migrate list`: 登録済み project-state migration を表示する。
- `pops migrate show <id>`: migration item の目的、checkpoint、移動内容を表示する。
- `pops migrate apply <id> [path] --dry-run`: migration の file operation を事前確認する。
- `pops migrate apply <id> [path]`: migration を適用する。
- `pops migrate [path] --apply`: 旧 scaffold に `.pops` 管理情報を追加する互換導線。
- `pops feedback`: 上流 `paperops` へ戻す改善フィードバックの下書きを出す。
- `pops links list [path]`: `_paperops/refs/links.toml` の外部 link を表示する。
- `pops links check [path]`: link registry と local location の対応を検証する。
- `pops workflow status [path]`: 論文全体と section の workflow state を表示する。
- `pops workflow next [path]`: 次に進める全体状態と guard の未達項目を表示する。
- `pops workflow advance <state> [path]`: guard が満たされた場合だけ全体状態を進める。
- `pops workflow invalidate <artifact-id> [path]`: claim / result / figure などに依存する section を stale にする。
- `pops workflow route-review [path] --issue-class <class> [--apply]`: review 指摘を evidence / story / section / prose / submission loop へ戻す。
- `pops scratch archive/restart/reset/restore/list/inspect`: 現在の論文作業層を `_archives/` の split bundle に封印し、同じ repo で1から書き直す。
- `pops version`, `pops --version`: CLI と上流情報を表示する。

## 更新対象

`update-paperops` が扱うのは、下流プロジェクトのハーネス管理面に限る。

- `AGENTS.md`
- `CLAUDE.md`
- `Makefile`
- `TROUBLESHOOTING.md`
- `_paperops/defaults/contracts/`
- `_paperops/defaults/workflow/`
- `scripts/`
- `.agents/`
- `.claude/`
- `.github/ISSUE_TEMPLATE/`
- `.github/PULL_REQUEST_TEMPLATE.md`

`README.md`、`story/`、`manuscript/`、`submission/`、`_paperops/contracts/`、`_paperops/workflow/current-state.yml`、`_paperops/workflow/decisions.yml`、`_paperops/workflow/round-summary.yml`、`_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/`、`_paperops/refs/`、`_paperops/notes/` はプロジェクト固有内容として自動更新しない。`manuscript/writing-profile.yml` は論文ごとの overlay なので、既存プロジェクトでは手動で追加・調整する。

project repo で paperops-managed core を直接編集し続けると update 時に drift が増える。通常は次の project-owned extension point を使う。

- `AGENTS.project.md`: Codex 向けの論文固有・チーム固有の恒久指示
- `CLAUDE.project.md`: Claude Code 向けの追加指示
- `Makefile.project`: Git 管理する project 固有 target
- `Makefile.local`: 個人環境だけの target や変数。`.gitignore` 対象
- `.agents/skills/project-*`, `.claude/skills/project-*`: project 固有 skill。`update-paperops` の managed update 判定から除外する

汎用化できる改善は project overlay に留め続けず、`/feedback-paper-harness` または `pops feedback` で upstream へ戻す。どうしても managed core 自体を project fork にする場合は、今後の detached fork manifest で明示的に扱う。

## Upgrade Chain

後方互換性を最新 `pops` に積み続けないため、scaffold 更新は checkpoint release を跨いで行える。

```sh
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply-chain
uvx --from paper-harness-cli pops update-paperops --target latest --allow-major --apply-chain
```

詳しい保持方針は [upgrade-policy.md](upgrade-policy.md) を参照する。

## Project-State Migrations

`update-paperops --apply-chain` は管理対象ハーネスファイルを checkpoint ごとに更新する。下流 project state の破壊的な移動や schema 変更は `pops migrate` の migration item として扱う。

たとえば `v1.1 -> v1.4` へ進む場合、`v1.2.x`、`v1.3.x`、`v1.4.x` を順に踏む。`v1.1 -> v1.2` の migration handler は `v1.2.x` が提供し、`v1.3.x` 以降へ無期限には持ち越さない。

```sh
uvx --from paper-harness-cli pops migrate list
uvx --from paper-harness-cli pops migrate show M0-0001
uvx --from paper-harness-cli pops migrate apply M0-0001 --dry-run
uvx --from paper-harness-cli pops migrate apply M0-0001
uvx --from paper-harness-cli pops migrate show M0-0002
```

現在の `M0-0001` は、旧 top-level の `contracts/`、`workflow/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` を `_paperops/` 配下へ移す。source と target の両方がある場合は conflict として停止し、ファイルは削除しない。`M0-0002` は `_paperops/defaults/` へ managed default を分離する guide-backed item で、既存 `_paperops/contracts/` や `_paperops/workflow/` の project overlay を自動削除しない。migration item の正本は [migrations/v0.md](migrations/v0.md) を参照する。

## Link Registry

共有可能な link intent は `_paperops/refs/links.toml` に置き、個人環境の絶対パスは ignored な `_paperops/refs/local/locations.toml` に置く。

```sh
uvx --from paper-harness-cli pops links list --resolve-local
uvx --from paper-harness-cli pops links check
```

`kind = "runops_project"` の link は、runops MCP から publication export、analysis artifact、survey summary、paper request queue を確認する入口として扱う。追加解析や図表要望は `_paperops/requests/analysis/` に切り出してから runops 側へ渡す。
下流 skill としては `/resolve-local-paths` が runops ディレクトリリンクの入口であり、`pops links list --resolve-local` と `pops links check` で `runops-main` の共有 link と個人環境パスを分けて確認する。

runops queue へ渡す予定の request は、下流 repo で `make research-request-handoff-check` または `make audit` を実行して確認する。通常は warning のみで、`python scripts/check-research-request-handoff.py --root . --strict` は投稿前や queue handoff の完了判定に使う。

外部 export bundle を図表・表・claim evidence に使う場合は、`_paperops/refs/imports/` に import state を記録し、`make external-import-check` または `make audit` を実行する。

## paper_ir

`paper_ir` は、card 正本と controlled authoring view から Writer に渡す context を作る生成一時物である。`pops` の永続管理対象ではなく、通常は skill が必要に応じて作る。手書き正本は `_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` に置き、`paper_ir` は Methods / Results / Discussion の section compiler へ渡す一時的な変換結果として扱う。

section compiler は、`_paperops/defaults/contracts/<section>.yml` の入出力契約、必要な `_paperops/contracts/<section>.yml` project overlay、`manuscript/writing-profile.yml` の paper type / venue overlay を重ねる。`plan-section` で作る一時 plan は必要なら `.paperops/cache/` に置き、Git 管理しない。

## Workflow

```sh
uvx --from paper-harness-cli pops workflow status
uvx --from paper-harness-cli pops workflow next
uvx --from paper-harness-cli pops workflow advance evidence-ready
uvx --from paper-harness-cli pops workflow invalidate CLM-0003
uvx --from paper-harness-cli pops workflow route-review --issue-class story-loop --apply
```

`_paperops/defaults/workflow/machine.yml` は固定の全体状態、section 状態、issue class、transition guard、loop policy を持つ。`_paperops/workflow/machine.yml` があれば project overlay として優先する。`_paperops/workflow/current-state.yml` は現在状態と section の `depends_on` を持つ。上流 artifact を更新した場合は `pops workflow invalidate <artifact-id>` で依存 section を `STALE` にし、review 後は `pops workflow route-review` で戻る深さを決める。

`submission_loop` は STRUCTURE_ACCEPTED 後の route である。`pops workflow route-review --issue-class submission-loop --apply` は、storyline / section / structure guard が未達なら拒否される。原稿完成作業中に author metadata、license、readiness-check、Makefile、script、skill 改修へ逸れそうな場合は、`make content-first-check` または `scripts/check-content-first.py --phase progress --intent <intent> --strict` で進路を確認する。

## Scratch Archives

```sh
uvx --from paper-harness-cli pops scratch archive --label before-rewrite
uvx --from paper-harness-cli pops scratch restart --label before-rewrite --yes
uvx --from paper-harness-cli pops scratch reset --yes
uvx --from paper-harness-cli pops scratch restore <archive-id> --yes
```

`pops scratch archive` は `story/`、`manuscript/`、`submission/` と `_paperops/notes/`、`_paperops/refs/`、`_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` を `_archives/<id>/archive.zip.partNNNN` に分割保存する。既定の part size は 48 MiB で、GitHub の単一ファイル制限にかからないようにする。

`pops scratch restart --yes` は archive 作成と reset を一操作で行う。`--include-handoff` を付けると `_handoff/` payload も封印してから starter 状態へ戻す。既存稿を残さず1から執筆へ戻したい場合は、`archive` と `reset` を別々に実行するより `restart` を使う。

`pops scratch reset --yes` は作業層と `_handoff/` payload を starter 状態に戻す。`_archives/` は残る。通常の AI 執筆では archive 内容を読まず、復元や比較を明示された場合だけ `pops scratch restore <id> --yes` を使う。

## 更新通知

TTY 上で通常コマンドが成功した場合、`pops` は低頻度で PyPI の最新版と `.pops/manifest.toml` の scaffold version を確認する。通知は非阻害で、無効化する場合は `POPS_DISABLE_VERSION_CHECK=1` を設定する。
