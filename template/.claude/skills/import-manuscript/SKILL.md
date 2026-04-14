---
name: import-manuscript
description: 既存の LaTeX 原稿をハーネス構造にインポートする。Overleaf や別リポジトリからの移行時に使用。
argument-hint: "<source-dir>"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# import-manuscript

既存の LaTeX 原稿をこのハーネスの構造にインポートする。Overleaf、別リポジトリ、ローカルディレクトリからの移行を支援する。

## 引数

- `<source-dir>`: インポート元のディレクトリパス（main.tex を含むディレクトリ）

## 手順

### 1. ソース解析

1. `<source-dir>/main.tex` を読み、以下を自動検出する:
   - document class（`\documentclass{...}`）
   - `\input` / `\include` で参照されるセクションファイル
   - `\bibliography` / `\addbibresource` で参照される bib ファイル
   - `\graphicspath` や図のディレクトリ
   - `\title`、`\author`、`\date` 等のメタデータ
2. ソースの言語を判定する（日本語 / 英語 / バイリンガル）。

### 2. セクションマッピング

ソースのセクションファイルをハーネスの命名規約にマッピングする:

| ハーネス名 | 対応するセクション |
|-----------|-----------------|
| `00_abstract.tex` | abstract |
| `10_intro.tex` | introduction |
| `20_method.tex` | method / model / theory |
| `30_results.tex` | results / analysis |
| `40_discussion.tex` | discussion |
| `90_conclusion.tex` | conclusion / summary |

- 対応が明確でないファイルはユーザーに確認する。
- 1ファイルに複数セクションが含まれる場合は分割を提案する。
- セクションが main.tex にインラインで書かれている場合は切り出す。

### 3. ブロック ID 付与

各セクションファイルに `% block:` ID を付与する:

- 既存のコメント区切り（`% ---`, `%%`, セクションコマンド）をヒューリスティックに利用
- `\section{}` や `\subsection{}` の直前に ID を配置
- ID の命名規則: `セクション名.サブセクション名.連番`
  - 例: `intro.background.01`, `method.model.01`, `results.scaling.01`

### 4. アセットのコピー

| ソース | コピー先 |
|-------|---------|
| bib ファイル | `manuscript/shared/bib/` |
| 図ファイル（png, pdf, eps 等） | `manuscript/shared/figures/` |
| スタイルファイル（cls, sty） | `manuscript/shared/style/` |
| テーブルファイル | `manuscript/shared/tables/` |

### 5. main.tex の生成

- document class をソースから維持する
- `\input` パスをハーネスの相対パス構造に修正
- bib パスを `../shared/bib/` に修正
- 図パスを `../shared/figures/` に修正

### 6. ミラー構造の構築

- ソースが日本語の場合: `manuscript/ja/` にコピーし、`manuscript/en/` にブロック ID のみのスケルトンを生成
- ソースが英語の場合: `manuscript/en/` にコピーし、`manuscript/ja/` にブロック ID のみのスケルトンを生成
- ソースがバイリンガルの場合: 両方を検出してマッピング
- `manuscript/mirror/map.toml` を生成

### 7. スキャフォールドのクリーンアップ

- スターターの frontmatter/ ディレクトリが不要なら削除
- ダミーのセクション内容を置き換え済みなら古いスターターファイルを削除

### 8. メタデータの自動補完

main.tex から検出した情報で以下を更新:
- `notes/project-brief.md`（title, author から）
- `manuscript/mirror/status.md`（ソースの言語をソースオブトゥルースとして記録）

### 9. 検証

```sh
make ci
```

## 出力

- インポートしたファイルの一覧
- セクションマッピングの結果
- 付与したブロック ID の一覧
- 手動確認が必要な項目（マッピング不明、パス解決不能等）
- `notes/decision-log.md` へのインポート記録

## 注意事項

- ソースファイルは変更しない（コピーのみ）。
- document class の変更は行わない（投稿先が指定する cls をそのまま使う）。
- bib キーの変更は行わない（既存の引用との整合性を維持）。
- 判断に迷う場合はユーザーに確認する。自動で全てを決定しない。
