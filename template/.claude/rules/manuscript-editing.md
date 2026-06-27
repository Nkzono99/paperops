# Glob: manuscript/**/*.tex

## 原稿編集ルール

- `% block: ...` 識別子を保持する。削除、名前変更、番号の振り直しを行わない。
- `manuscript/mirror/status.md` に別段の記載がない限り、日本語（`ja/`）がソースオブトゥルースである。
- ja/ セクションを編集した後は、後の `/sync-ja-en` のために影響を受けたブロック ID をメモする。
- 通読レビュー中に直しきれない違和感は `% REVIEW:`, `% AI:`, `% Q:`, `% KEEP?:`, `% INTENT:`, `% TODO-PAPER:` の TeX コメントで残し、後で `/collect-manuscript-review` に回収させる。AI Writer の執筆意図、後で埋める内容、作業計画は本文 prose に書かない。
- `manuscript/shared/figures/generated/` 配下のファイルを直接編集しない。
- `\input` パスは原稿ルートからの相対パスにする。
