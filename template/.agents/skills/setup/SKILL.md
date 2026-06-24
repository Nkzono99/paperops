---
name: setup
description: テンプレートから作成した新しい論文リポジトリの初回セットアップを一括で行う。プロジェクト開始時に使用。
---

# setup

`pops init` 直後の論文リポジトリを、作業を始められる最小状態にする。初回 setup は構造、ローカル安全性、公開 metadata を整える lane であり、論文の claim 設計や文献調査を深掘りしすぎない。

## 前提

- `pops init` で `paperops` から生成した repository である。
- 既存内容を上書きせず、placeholder または未記入項目だけを埋める。
- `refs/local/locations.toml` は個人パスを含みうるため AI は自動作成・自動編集しない。

## 軽量確認

最初は存在確認と placeholder 検出だけを行い、重い意味論ノートを全部読まない。

常時確認する:

- `README.md` に `paper-my-topic` が残っているか
- `.pops/manifest.toml`、`.venv/`、`tex-env.toml` の有無
- `refs/local/locations.example.toml` と `refs/local/locations.toml` の有無
- `_handoff/`、`_handoff/README.md`、`_handoff/.gitkeep` の有無
- `evidence/`、`claims/`、`review/`、`requests/`、`notes/views/` の有無
- `.gitignore` が `_handoff/*` と `refs/source-reach/**/raw/**` を保護しているか
- `.github/workflows/*.yml` に `YOUR_ORG/paperops` が残っているか
- `manuscript/publication-metadata.toml` と `manuscript/venue.md` の placeholder
- `notes/project-brief.md` と `notes/contribution-claims.md` の placeholder

必要時に読む:

- claim / evidence を初期化する時だけ `notes/views/scientific-gate.md`、`notes/views/claim-evidence-map.md`
- 関連研究を初期化する時だけ `notes/related-work-map.md`、`notes/source-reach.md`
- 読者や投稿先を初期化する時だけ `notes/reviewer-model.md`、`notes/views/peer-review.md`
- AI draft や AI 利用方針を確認する時だけ `notes/ai-draft-polish.md`、`notes/ai-use.md`
- 再現性の初期値が必要な時だけ `notes/reproducibility.md`

## 情報収集

一度にまとめて聞く:

- repository 名
- 論文トピック
- 公開タイトル（日本語・英語、未定可）
- 著者
- 上流 `paperops` repository（例 `Nkzono99/paperops`）
- 投稿先候補、締切、ページ制限（未定可）
- TeX 環境（未定なら system default）
- 原稿、コード、データの公開ライセンス（未定可）

## 実行経路

`pops` は project-local `.venv` ではなく `uvx` から実行する。`.pops/manifest.toml` が無い場合は次を案内または実行する。

```sh
uvx --from paper-harness-cli pops setup
```

論文プロジェクト用の Python 環境が必要な場合だけ `make venv` を使う。`.venv` に `pops` を入れる必要はない。

## ローカル安全性

`refs/local/locations.toml` が無い場合は、ユーザーに copy command と編集方針だけを案内する。

```sh
cp refs/local/locations.example.toml refs/local/locations.toml
```

```powershell
Copy-Item refs/local/locations.example.toml refs/local/locations.toml
```

`_handoff/` は人間から AI へ渡す未整理ファイルの一時受け取り箱として使う。無い場合は `_handoff/README.md` と `_handoff/.gitkeep` を用意し、`.gitignore` に次を保持する。

```gitignore
_handoff/*
!_handoff/.gitkeep
!_handoff/README.md
refs/source-reach/**/raw/**
refs/source-reach/**/doctor.generated.*
refs/source-reach/**/capture.generated.*
```

`tex-env.toml` は、ユーザーが TeX Live path や Docker image を提供した場合だけ `tex-env.example.toml` から作る。

## 初期反映

- `.github/workflows/*.yml` の `YOUR_ORG/paperops` を実際の上流 repository に置換する。
- `README.md` の repository 名と 1 行説明を更新する。
- `notes/project-brief.md` にトピック、目標、著者を入れる。
- `manuscript/venue.md` は投稿先候補がある場合だけ埋める。
- `manuscript/publication-metadata.toml` に title、authors、repository URL、upstream、license を入れる。未定項目は placeholder のまま残してよい。
- `notes/contribution-claims.md` は、具体化できる範囲だけ仮 claim を置く。弱い claim は TODO にする。

## 意味論スターター

必要時だけ、次の starter を薄く埋める。未確定なら TODO のまま残す。

- related work: `/research-related-work` に渡す初期 scope、source cluster、debate axis。
- source reach: 外部 Web、GitHub、動画、RSS、SNS、議論サイトを使う可能性と raw capture 方針。
- card layers: `evidence/README.md`、`claims/README.md`、`review/README.md`、`requests/README.md` を確認し、カード層を正本、`notes/views/` を俯瞰ビューとして扱う。
- scientific gate: Abstract / Conclusion / main figure caption に出す前の gate status。evidence 未確定なら `analysis-needed` または `assumption-blocked` のままにする。
- claim-evidence map: Core claim、essential results、Not claiming の仮案。evidence 未確定なら `draft` のままにする。
- reviewer model / peer review: 投稿先候補、想定読者、likely skepticism、AI review / confidentiality の TODO。
- AI use / polish: AI 初稿を使う場合の claim lock、polish log、AI 利用方針。
- reproducibility: 入力データ、解析環境、figure provenance、既知の非再現ステップ。

## 検証

初回 setup 後は可能なら次を実行する。

```sh
make ci
```

外部共有や投稿に近い状態まで埋まっている場合だけ `make pre-submit` も実行する。難しい場合は `make lint-bib`、`make citation-check`、`make mirror-check` を個別に実行する。

## 出力

- 実行した手順
- スキップした手順と理由
- 手動で残す作業（`refs/local/locations.toml`、venue、metadata、reproducibility など）
- 次の推奨ステップ（例: `/resume-session`、`/research-related-work`、`/scientific-gate`）

## Codex 実行メモ

- 編集前に軽量確認を行い、必要時に読むリストだけ追加で開く。
- Core claim、reader model、AI use log は埋められる範囲だけ starter として更新し、未定なら TODO にする。
- `refs/local/locations.toml` は自動作成・自動編集しない。
- セットアップの決定は `notes/decision-log.md` に短く記録する。
