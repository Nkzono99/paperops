---
name: archive-scratch
description: 過去稿を封印して1から書き直す、scratch archive を一覧・確認・復元する、または _archives/ の扱いを判断するときに使う。
---

# archive-scratch

過去稿を同じ repo 内で封印し、必要なら作業層を starter 状態へ戻す。通常の執筆やレビューでは `_archives/` を読まず、ユーザーが archive の inspect / restore / compare を明示した場合だけ扱う。

## まず確認すること

- `pops` は `uvx --from paper-harness-cli pops ...` で実行する。
- 現在地が paper project root か不明なら `uvx --from paper-harness-cli pops doctor` を先に実行する。
- archive は `manuscript/`、`submission/`、`_paperops/notes/`、`_paperops/refs/`、`_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` を sealed split bundle として `_archives/<id>/` に置く。
- `_handoff/` は既定では含めない。人間が明示した場合だけ `--include-handoff` を使う。
- `archive` は封印だけを行い、現行の作業層は残る。1から執筆へ戻す場合は `restart` を使う。
- reset / restart / restore は破壊的操作である。ユーザーが対象 archive id または reset の実行意思を明示していない場合は、`--yes` を付けて実行しない。

## 封印する

1. 何を封印するかを一文で label にする。
2. 次を実行する。

```sh
uvx --from paper-harness-cli pops scratch archive --label "before major rewrite"
```

特定 ID が必要な場合だけ `--id <safe-id>` を付ける。大きい bundle でも `archive.zip.partNNNN` に分割されるため、手で zip を展開して保存しない。

封印後に確認する。

```sh
uvx --from paper-harness-cli pops scratch list
make archive-seal-check
```

## 書き直す

現行稿を封印してから現在の作業層を starter へ戻す。通常はこちらを使う。

```sh
uvx --from paper-harness-cli pops scratch restart --label "before major rewrite" --yes
```

`_handoff/` payload も封印したいと明示された場合は `--include-handoff` を付ける。archive 作成済みで reset だけ行う場合は次を使う。

```sh
uvx --from paper-harness-cli pops scratch reset --yes
```

archive なしで reset するのは例外扱いにする。人間が「archive なしでよい」と明示した場合だけ `--allow-without-archive` を使う。

## 確認・復元

中身を直接読まず、まず metadata を見る。

```sh
uvx --from paper-harness-cli pops scratch list
uvx --from paper-harness-cli pops scratch inspect <archive-id>
```

復元は現在の `manuscript/`、`submission/`、`_paperops/notes/`、`_paperops/refs/`、`_paperops/evidence/`、`_paperops/claims/`、`_paperops/review/`、`_paperops/requests/` を置き換える。ユーザーが対象 ID と復元を明示した場合だけ実行する。

```sh
uvx --from paper-harness-cli pops scratch restore <archive-id> --yes
```

過去稿との比較を頼まれた場合も、通常の執筆 context と混ぜない。まず `pops scratch inspect` で対象を確認し、必要なら一時 copy や別作業として比較する方針を人間に短く確認する。

## 出力

- 実行した `pops scratch ...` コマンド
- 作成または対象にした archive id
- `_handoff/` を含めたか
- `make archive-seal-check` の結果
- restart / reset / restore を実行した場合、置き換えた範囲と残る `_archives/`

## Codex 実行メモ

- `_archives/` 配下の展開済み本文を直接読んで通常の原稿改善に使わない。
- `archive.zip.partNNNN` を手で結合・展開して tracked tree に置かない。
- 生成された archive bundle は、共有・commit 対象かどうかを人間に確認する。機密や未整理 input が入る可能性がある。
