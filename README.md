# paperops

## PaperOps 2 1.0

新規`pops init`はResearch / Editorial / Results hierarchy / Manuscript / Issue / Publicationの六モデルだけを権威として作る。通常の構造化変更は`pops change`がindex、revision/hash、依存検証、manifest、journal、rollbackを処理する。旧cardとmacro-stateは新規scaffoldに含めないが、既存projectのartifactは`setup`やmanaged updateで削除せず、`pops model` / `pops workflow migrate`のread-only migration readerを維持する。

`paperops` は、AI エージェントと論文を書くためのプロジェクトハーネスである。

人間が `template/` を手でコピーして使う道具ではなく、`pops` CLI で論文プロジェクトを初期化・診断・更新する。

## まず使う

新規論文プロジェクト:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

この新規projectは六モデルのstarterを検証し、そのsemantic hashとtyped workflowを`.pops/manifest.toml`へ原子的に記録する。既存projectをv2へ移す場合は`pops init --force`で権威を上書きせず、`pops model diff|adopt`と`pops workflow migrate`を使う。

既存プロジェクトを `pops` 管理に寄せる:

```sh
uvx --from paper-harness-cli pops setup
uvx --from paper-harness-cli pops doctor
```

`pops` は常に `uvx --from paper-harness-cli pops ...` で実行する。`.venv` は CLI 用ではなく、論文プロジェクト側の Python 実行環境が必要な場合に `make venv` で作る。

## 何を提供するか

- `template/`: 個別論文リポジトリに展開される scaffold
- `src/paperops/`: scaffold を初期化・診断・更新する `pops` CLI
- `.github/workflows/`: 下流論文リポジトリから呼び出せる reusable workflow
- `.agents/skills/`, `.claude/skills/`: paperops 自体を保守するための skill
- `docs/`: CLI、配布、アーキテクチャ、変更ルール

## 論文プロジェクトの基本モデル

下流の論文リポジトリでは、原稿だけでなく中間層も明示的に持つ。

- `_paperops/model/research/`: claim / result / figure / source / scientific gate
- `_paperops/model/editorial/`: story decision と Results hierarchy
- `_paperops/model/manuscript/`: section / block topology と operation
- `_paperops/model/issues/`: feedback / request / response / review round / workflow issue
- `_paperops/model/publication/`: submission candidate / approval / round snapshot reference
- `_paperops/notes/views/`: pure overview view と controlled authoring view
- `_paperops/model/editorial/results-hierarchy.yml`: project-owned の typed Results hierarchy 正本
- `_paperops/defaults/schemas/`: paperops-managed の schema default
- `_paperops/defaults/contracts/`: paperops-managed の標準 section / figure story 契約
- `_paperops/contracts/`: 論文固有の contract overlay
- `pops workflow status`: 六モデルから全体状態、review、submission、section、staleを投影
- `manuscript/writing-profile.yml`: 論文種別・投稿先ごとの overlay
- `manuscript/ja`, `manuscript/en`: block ID で対応する原稿
- `_paperops/refs/`: 文献サマリー、外部 source、外部 project link
- `_paperops/refs/imports/`: 外部 export bundle の source index / integrity / provenance state
- `_handoff/`: 人間から AI へ渡す未整理ファイルの一時置き場
- `_archives/`: 同じ repo で1から書き直すために封印した過去稿 archive

人間は主に原稿レベルのレビューや自然文の指示を出す。Agent はそれを `_paperops/model/issues/feedback/` の card にし、必要なら claim / gate / evidence / request / manuscript へ遡って反映する。本文生成の前には、必要に応じて `pops workflow status`、`_paperops/defaults/contracts/`、`_paperops/contracts/`、`manuscript/writing-profile.yml` を確認し、`plan-figure-story` で visual obligation と主図構成を決めてから、card と controlled view から `paper_ir` を作り、Results / Discussion / Methods の section compiler を通す。

新規 scaffold ではtyped modelだけを使う。既存下流 projectのlegacy artifactは移行完了まで読み取り可能であり、1.0.0への更新だけでは削除されない。

PaperOps 2 P1-B は Research、Editorial、Results hierarchy、Manuscript、Issue、Publication の正確な六モデルを提供する。P2 は `pops model` の deterministic migrationとして、legacy inventory、shadow diff、strict validation、model単位のadopt、snapshot rollbackをAIなしで反復できるようにする。authorityは`legacy-authoritative`、`shadow-compare`、`v2-authoritative`をmodelごとに持ち、Editorial / Results hierarchyだけはcompanionとして同時に切り替える。

AI Agentはscientific / editorial judgment、候補の選択理由、未解決fieldを埋めるための人間との対話を担当し、定型的なfile discovery、hash、conservation、transaction、recoveryを直接操作しない。P3 compiler / WriterとP4 workflow writerの導入後もhuman-edited living TeXを維持する。legacy互換artifactは新規scaffoldから削除済みで、既存projectのproject-owned artifactだけを明示migrationと確認が終わるまで保持する。

検証phaseは schema → references → semantics → canonical semantic-v1 hash の順で、mechanism-led、boundary-led、negative-result-led の三つの合成fixtureを回帰corpusとして維持する。

## よく使うコマンド

```sh
uvx --from paper-harness-cli pops version
uvx --from paper-harness-cli pops doctor
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply
uvx --from paper-harness-cli pops links check
uvx --from paper-harness-cli pops model status all
uvx --from paper-harness-cli pops model diff research
uvx --from paper-harness-cli pops model adopt research --yes
uvx --from paper-harness-cli pops model rollback research
uvx --from paper-harness-cli pops change plan .paperops/request.yml
uvx --from paper-harness-cli pops change apply CHG-... --yes
uvx --from paper-harness-cli pops compile prepare all
uvx --from paper-harness-cli pops write start CMP-...
uvx --from paper-harness-cli pops scratch archive --label before-rewrite
uvx --from paper-harness-cli pops scratch reset --yes
```

下流プロジェクトでの確認:

```sh
make ci
make audit
make schema-check
make pre-submit
make figure-reference-check
make figure-obligation-check
```

paperops 本体の確認:

```sh
make venv
make smoke
```

## 詳細

- PaperOps 2 設計 RFC: [docs/rfcs/0001-paperops-2.md](docs/rfcs/0001-paperops-2.md)
- CLI: [docs/cli.md](docs/cli.md)
- 配布とリリース: [docs/distribution.md](docs/distribution.md)
- アーキテクチャ: [docs/architecture.md](docs/architecture.md)
- Skill 一覧: [docs/skill-catalog.md](docs/skill-catalog.md)
- 更新方針: [docs/upgrade-policy.md](docs/upgrade-policy.md)
- 変更ルール: [docs/change-policy.md](docs/change-policy.md), [docs/triage-rules.md](docs/triage-rules.md)
