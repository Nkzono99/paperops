# アーキテクチャ

`paperops` は、テンプレート保守と個別論文執筆を分ける。

## ルート層

リポジトリルートは、下流論文リポジトリへ配るものを管理する。

- `template/`: bundled scaffold の source of truth
- `src/paperops/`: `pops` CLI
- `.github/workflows/`: reusable workflow
- `.github/ISSUE_TEMPLATE/`: テンプレート改善の受け口
- `.agents/skills/`, `.claude/skills/`: テンプレート保守 skill
- `docs/`, `CHANGELOG.md`: 変更方針と配布記録

この層の役割は、ハーネスを安全に進化させることである。

## 下流論文層

`template/` は個別論文リポジトリに展開される。主な層は次の通り。

- `manuscript/`: 日英原稿、ミラー制御、投稿先情報
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX
- `refs/`: 文献サマリー、関連研究調査、外部 source、外部 project link、外部 bundle import state
- `_handoff/`: 人間から AI へ渡す未整理ファイル
- `_archives/`: 過去稿を sealed split bundle として封印する scratch archive
- `evidence/`: result / figure / source card
- `claims/`: claim / scientific gate / argument card
- `review/`: feedback / review round / response card
- `requests/`: analysis / writing request card
- `notes/`: project brief、読者モデル、AI 利用、再現性、`notes/views/`

`evidence/`、`claims/`、`review/`、`requests/` がカード正本で、`notes/views/` は人間が俯瞰するビューである。`notes/views/concept-terms.md` は、claim / argument / evidence card の意味を本文の語彙へ圧縮するときの概念語ビューとして扱い、単語化された表現を採用・展開・禁止へ分ける。旧 `notes/*.md` の一部は互換ビューとして残す。

## 情報フロー

1. 人間は主に原稿レビュー、自然文の指示、判断を出す。
2. Agent は必要に応じて feedback / evidence / claim / request card を更新する。
3. Abstract、Conclusion、主要図表に使う claim は `claims/gates/` で readiness を確認する。
4. 本文に出る強い名詞句は `notes/views/concept-terms.md` で確認し、accepted term、普通の文へほどく語、avoid 語を分ける。
5. 原稿修正は最後に行う。本文だけ直して上流の claim や evidence を放置しない。
6. 外部 project や runops の成果物は `refs/links.toml`、`refs/local/locations.toml`、`refs/imports/` で link、実パス、import state を分ける。
7. 1から書き直す評価では、`pops scratch archive` で現行層を `_archives/` に封印し、`pops scratch reset` で作業層だけを初期化する。通常の Agent workflow は `_archives/` を読まない。

## 設計原則

- 下流作成は `pops init` に統一する。
- `pops update-paperops` はハーネス管理ファイルだけを更新し、下流固有の原稿・notes・refs・カードを自動上書きしない。
- 作業用ドキュメントは原則日本語で書く。識別子、citation key、TOML field name は英語のままでよい。
- raw PDF、未整理ファイル、個人環境の絶対パス、confidential correspondence は tracked な共有ファイルへ混ぜない。
- 検証はローカルでも CI でも短時間で回せる粒度に保つ。
