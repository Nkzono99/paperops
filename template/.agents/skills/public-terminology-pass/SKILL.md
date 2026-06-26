---
name: public-terminology-pass
description: ローカル語・内部語・未定義略語を公開語へ置換し、terminology.yml と本文の初出定義を整える。
---

# public-terminology-pass

repo や run folder を知らない読者に通じない語を公開語へ変換する。
runops project、publication export bundle、raw run directory、run label、campaign、case、production run、smoke/feasibility check、script name、artifact name は本文では内部 provenance 語として扱う。

## 最初に読むファイル

- `manuscript/mirror/terminology.yml`
- `_paperops/notes/views/concept-terms.md`
- 対象の公開原稿 TeX
- 必要に応じて `_paperops/notes/reviewer-model.md`

## 手順

1. local term、run label、script name、directory name、artifact name、未定義略語を抽出する。
2. hyphen / slash compound や強い英語名詞句は concept-term compression として `_paperops/notes/views/concept-terms.md` に分け、public terminology と混同しない。
3. 各語を `public` / `needs_definition` / `internal_only` / `forbidden` に分類する。
4. `en_public`、first-definition sentence、figure label replacement を提案する。baseline 名、図中だけの略語、decision criterion、threshold、保存時点や case count 名も抽出対象にする。内部 provenance 語は analysis workflow、analysis dataset、figure-data package、regeneration manifest、exploratory check、simulation condition、localized physical region などへ置換する。
5. `manuscript/mirror/terminology.yml` を更新し、`needs_definition` では `first_definition_location` が実在する本文 file を指すようにする。
6. 本文・figure caption・section heading に残る内部語を置換する。概念語は accepted でなければ普通の文へほどく。
7. `make public-terms-check` と `make concept-term-check` を実行する。完了前には `scripts/check-public-terms.py --root . --strict` で定義位置に実際の definition sentence があることを確認する。

## 出力

- 置換した用語表
- 初出定義を追加した箇所
- 残した内部語と理由
- `make public-terms-check` の結果

## Codex 実行メモ

- `manuscript/mirror/terminology.yml` を gate として使う。
- 本文、figure caption、section heading の local term を public term に置換し、`needs_definition` の初出位置には `refers to`、`defined as`、`とは`、`を意味する` などの定義文を置く。
- `_paperops/refs/links.toml`、`_paperops/refs/local/locations.toml`、export 名、run label、path は本文へ直書きしない。必要な provenance は `_paperops/notes/reproducibility.md` や `_paperops/refs/` の日本語作業メモに分離する。
- concept term は `_paperops/notes/views/concept-terms.md` で accepted / plain-language / avoid を分ける。
- 最後に `make public-terms-check` と `make concept-term-check` を実行し、finish 前は strict public terms check も通す。
