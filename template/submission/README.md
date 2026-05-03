# submission

投稿先公式テンプレートや最終提出用 TeX は `submission/<venue>/` に分離する。

## 使い分け

- `manuscript/ja/` と `manuscript/en/` は、論理構成と日英ミラーを育てるためのハーネス原稿。
- `submission/<venue>/` は、JGR、AGU、Elsevier、arXiv、会議テンプレートなど投稿先固有の最終整形領域。
- 公式テンプレートの `.cls`、`.sty`、logo、supplement template、投稿用 build script は `submission/<venue>/` の中に閉じる。
- build output や投稿先テンプレート用のローカルツールは Git に含めない。

## 推奨レイアウト

```text
submission/
  jgr-space-physics/
    README.md
    main.tex
    figures/
    style/
    build/
```

## 同期方針

1. `manuscript/ja/` で科学的な論理を固める。
2. 必要なブロックを `manuscript/en/` にミラーする。
3. 投稿先が固まったら `manuscript/venue.md` に制約と `submission/<venue>/` の場所を書く。
4. `manuscript/en/` の公開本文を `submission/<venue>/main.tex` に展開し、投稿先固有の class/style に合わせる。
5. 投稿版で生じた科学的変更は `manuscript/` 側にも戻し、二重管理にしない。
