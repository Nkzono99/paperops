# manuscript

`manuscript/` は論文本文の作業層である。

- `ja/`: 既定の source-of-truth 原稿。科学的意味を変える編集はまずここで行う。
- `en/`: 英語 mirror。`ja/` の block と対応させ、必要な範囲で `sync-ja-en` を使って同期する。
- `mirror/`: block ID、terminology、change queue、同期状態を管理する。
- `shared/`: 両言語で共有する style、bib、figure などを置く。
- `publication-metadata.toml`: 投稿・共有に必要な metadata を置く。
- `venue.md`: 投稿先、読者、投稿規程、AI 利用開示の確認先を置く。

`submission/` は投稿先に合わせた提出版スロットであり、原稿正本ではない。投稿版で科学的意味を変えた場合は、必ず `manuscript/` 側へ戻す。

Writer は `evidence/`、`claims/`、`review/`、`requests/` と controlled authoring view から作った `paper_ir` を使い、Methods / Results / Discussion の reader question、answer、evidence、figure、caveat location を確認してから本文を書く。
