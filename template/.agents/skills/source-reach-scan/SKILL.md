---
name: source-reach-scan
description: 外部 Web、GitHub、論文ページ、動画、RSS、SNS、議論サイトなどから情報を集める前に、到達経路、認証、raw 保存先、refs への昇格方針を決めるときに使う。
---

# source-reach-scan

外部情報源を「検索して貼る」のではなく、source type ごとに到達経路、検証状態、保存先、昇格先を分けるために使う。

Agent Reach の channel / backend / doctor の発想を paperops の refs 層へ移したもの。paperops は Agent Reach を依存関係として要求しない。利用環境に `agent-reach` が入っている場合だけ補助的に `agent-reach doctor --json` を使ってよい。

## 最初に読むファイル

- `notes/source-reach.md`
- `notes/related-work-map.md`
- `notes/research-requests.md`
- `notes/reproducibility.md`
- `refs/research/README.md`
- `refs/source-reach/README.md`
- `refs/links.toml`
- `refs/local/locations.example.toml`
- 必要に応じて `manuscript/venue.md`、`notes/scientific-gate.md`

## Source channels

`notes/source-reach.md` の channel table を更新する。

| channel | 例 | 既定の扱い |
| --- | --- | --- |
| `paper-metadata` | DOI、arXiv、出版社ページ | web で確認し、採用時は `.bib` と `refs/summaries/` へ昇格 |
| `github` | repo、issue、release、code | GitHub CLI / web / clone。commit hash と license を残す |
| `web-page` | project docs、blog、policy | web で確認し、引用に使うなら取得日と URL を残す |
| `video-transcript` | YouTube、講演、チュートリアル | transcript の取得可否と信頼性を記録。本文証拠には慎重に使う |
| `rss-news` | 更新監視、ニュース | current info として日付を明記 |
| `social-discussion` | Reddit、X、V2EX、小紅書など | 研究背景や実務動向の探索に留め、主証拠にしない |
| `local-link` | 外部 project、runops、データディレクトリ | `refs/links.toml` と `refs/local/` で解決 |

## 手順

### 1. 調査目的を固定する

関連研究、先行実装、研究動向、読者反応、投稿先 policy、再現性 artifact のどれを調べるか決める。未公開原稿や private note の文面を検索語にしない。

### 2. Channel routing を決める

各 source ごとに、preferred route、fallback route、credential need、raw capture policy、promotion target を決める。

利用可能なら次を確認する。

```sh
agent-reach doctor --json
```

入っていない場合は、Codex の web、GitHub CLI、ローカル clone、通常の PDF/文書処理で進める。`agent-reach` のインストールや cookie 設定は、ユーザーが明示した場合だけ提案する。

### 3. Raw capture と curated output を分ける

- raw search result、HTML、transcript、SNS dump は `refs/source-reach/<topic-slug>/raw/` か `refs/research/<topic-slug>/results/` に置き、既定では Git 管理しない。
- 人間が確認した要約だけを `notes/source-reach.md`、`notes/related-work-map.md`、`refs/summaries/`、`notes/reproducibility.md` へ昇格する。
- confidential、cookie、token、個人環境の絶対パスは tracked file に残さない。

### 4. Verification を付ける

各 finding に verification status を付ける。

- `unsearched`
- `found-unread`
- `metadata-checked`
- `read`
- `cross-checked`
- `not-usable`

現在性が重要な情報は具体日付を残す。論文 metadata、ソフトウェア仕様、投稿先 policy、外部 repository は web で確認し、出典リンクを残す。

### 5. 後段へ渡す

- 関連研究へ使う: `/research-related-work`
- 引用へ使う: `/update-refs`
- claim gate へ使う: `/scientific-gate`
- 再現性へ使う: `notes/reproducibility.md`
- 外部 project path へ使う: `/resolve-local-paths`

## 出力

- `Reach objective`
- `Channel routing table`
- `Doctor / availability result`
- `Raw capture policy`
- `Curated promotion targets`
- `Verification status`
- `Privacy / credential risks`
- `Next routes`

## Codex 実行メモ

- 外部検索や GitHub 内容は古くなりうるため、必要に応じて web で確認し、リンクを残す。
- credential や cookie の設定、SNS ログイン、外部サービスへのアップロードはユーザー承認なしに行わない。
- `refs/` と `notes/` の作業用ドキュメントは日本語で書く。
