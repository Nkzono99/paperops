# Glob: manuscript/**/*.tex

## 原稿編集ルール

- `% block: ...` 識別子を保持する。削除、名前変更、番号の振り直しを行わない。
- `manuscript/mirror/status.md` に別段の記載がない限り、日本語（`ja/`）がソースオブトゥルースである。
- ja/ セクションを編集した後は、後の `/sync-ja-en` のために影響を受けたブロック ID をメモする。
- `manuscript/shared/figures/generated/` 配下のファイルを直接編集しない。
- `\input` パスは原稿ルートからの相対パスにする。
