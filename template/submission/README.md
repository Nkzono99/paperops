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
6. 投稿前は `make pre-submit` を実行し、`submission/<venue>/README.md` または `submission/<venue>/main.tex` の存在と drift を確認する。

## PDF build

既定では `make build-submission VENUE=<venue>` は `submission/<venue>/main.tex` の構造検証だけを行う。PDF 実ビルドは opt-in で、TeX 環境がある場合に次を使う。

```sh
PAPER_TEMPLATE_RUN_LATEX=1 make build-submission VENUE=<venue>
```

`scripts/build-submission.sh` は `submission/<venue>/build/` に出力し、`submission/<venue>/style/`、`manuscript/shared/style/`、`manuscript/shared/bib/`、`refs/bib/` を TeX/BibTeX の探索対象に加える。`latexmk` がなければ `PAPEROPS_SUBMISSION_DIRECT_ENGINE` または `lualatex -> xelatex -> pdflatex` の順で direct-engine fallback を試す。fallback 中の `bibtex main` は build directory から走るため、`BIBINPUTS` / `BSTINPUTS` は repository root からの絶対パスで設定される。HPC や CI で実行 prefix が必要な場合は `PAPEROPS_RUNNER_PREFIX` を使う。

PDF 生成後は `scripts/audit-build-log.py` が fatal error、undefined citation/reference、Missing character、BibTeX database error、empty bibliography を確認する。投稿先固有の `.cls` / `.sty` / `.bst` の由来は、このディレクトリの README に記録する。
