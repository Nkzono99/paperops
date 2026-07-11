# paperops

`paperops` は、AI エージェントと論文を書くためのプロジェクトハーネスである。

人間が `template/` を手でコピーして使う道具ではなく、`pops` CLI で論文プロジェクトを初期化・診断・更新する。

## まず使う

新規論文プロジェクト:

```sh
uvx --from paper-harness-cli pops init paper-my-topic
cd paper-my-topic
uvx --from paper-harness-cli pops doctor
```

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

- `_paperops/evidence/`: result / figure / source card の正本
- `_paperops/claims/`: claim / scientific gate / argument card の正本
- `_paperops/review/`: 人間レビュー、査読コメント、返答のカード
- `_paperops/requests/`: 追加解析や改稿依頼のカード
- `_paperops/notes/views/`: pure overview view と controlled authoring view
- `_paperops/model/editorial/results-hierarchy.yml`: project-owned の typed Results hierarchy 正本
- `_paperops/defaults/schemas/`: paperops-managed の schema default
- `_paperops/defaults/contracts/`: paperops-managed の標準 section / figure story 契約
- `_paperops/contracts/`: 論文固有の contract overlay
- `_paperops/workflow/`: 全体状態、section 状態、review loop、stale 伝播
- `manuscript/writing-profile.yml`: 論文種別・投稿先ごとの overlay
- `manuscript/ja`, `manuscript/en`: block ID で対応する原稿
- `_paperops/refs/`: 文献サマリー、外部 source、外部 project link
- `_paperops/refs/imports/`: 外部 export bundle の source index / integrity / provenance state
- `_handoff/`: 人間から AI へ渡す未整理ファイルの一時置き場
- `_archives/`: 同じ repo で1から書き直すために封印した過去稿 archive

人間は主に原稿レベルのレビューや自然文の指示を出す。Agent はそれを `_paperops/review/feedback/` の card にし、必要なら claim / gate / evidence / request / manuscript へ遡って反映する。本文生成の前には、必要に応じて `pops workflow status`、`_paperops/defaults/contracts/`、`_paperops/contracts/`、`manuscript/writing-profile.yml` を確認し、`plan-figure-story` で visual obligation と主図構成を決めてから、card と controlled view から `paper_ir` を作り、Results / Discussion / Methods の section compiler を通す。

新規 scaffold では typed Results hierarchy を使う。既存下流 project は M0-0003 採用まで legacy Markdown fallback を維持でき、移行時は managed schema default を更新したうえで project-owned typed state を opt-in で作成する。

PaperOps 2 は P1-A の Editorial Model 縦切りに加え、P1-B Task 3〜5 の Research / Manuscript / Issue Model schema、空 starter index、意味検証を提供する。Issue Model は feedback、analysis / writing request、response、review round を型付き record とし、raw confidential text や絶対 path を保存せず、解析 lifecycle と response closure を検査する。managed registry / schema / checker と project-owned model state を分離し、legacy card の authority は維持する。Publication Model、全 model cross-reference、dependency target 解決は未提供である。

検証phaseは schema → references → semantics → canonical semantic-v1 hash の順で、mechanism-led、boundary-led、negative-result-led の三つの合成fixtureを回帰corpusとして維持する。

## よく使うコマンド

```sh
uvx --from paper-harness-cli pops version
uvx --from paper-harness-cli pops doctor
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply
uvx --from paper-harness-cli pops links check
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
