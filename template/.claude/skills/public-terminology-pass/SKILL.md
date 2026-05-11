---
name: public-terminology-pass
description: ローカル語・内部語・未定義略語を公開語へ置換し、terminology.yml と本文の初出定義を整える。
argument-hint: "[section-or-scope]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# public-terminology-pass

repo や run folder を知らない読者に通じない語を公開語へ変換する。

## 最初に読むファイル

- `manuscript/mirror/terminology.yml`
- 対象の公開原稿 TeX
- 必要に応じて `notes/reviewer-model.md`

## 手順

1. local term、run label、script name、directory name、artifact name、未定義略語を抽出する。
2. 各語を `public` / `needs_definition` / `internal_only` / `forbidden` に分類する。
3. `en_public`、first-definition sentence、figure label replacement を提案する。
4. `manuscript/mirror/terminology.yml` を更新する。
5. 本文・figure caption・section heading に残る内部語を置換する。
6. `make public-terms-check` を実行する。

## 出力

- 置換した用語表
- 初出定義を追加した箇所
- 残した内部語と理由
- `make public-terms-check` の結果
