# refs/research

関連研究を広く集めるための一時調査領域。

このディレクトリは、Deep-Research-skills の outline -> deep research -> report という発想を paperops 用に薄く取り込むために使う。raw web findings や item ごとの JSON / Markdown は、論文の正本ではない。採用する文献だけを `refs/summaries/`、`manuscript/shared/bib/references.bib`、`notes/related-work-map.md` へ昇格する。

## 推奨構造

```text
refs/research/<topic-slug>/
  outline.toml          # 調査対象 item と実行方針
  fields.toml           # item ごとに集める観点
  discussion.md         # 調査後の議論メモ
  results/              # raw item research。既定では Git 管理しない
  report.generated.md   # raw 統合レポート。既定では Git 管理しない
```

## tracked にするもの

- 調査設計として再利用したい `outline.toml`
- 調査観点として共有したい `fields.toml`
- 人間が確認して整理した `discussion.md`
- 文献レビューの正本に近い内容へ整理した `notes/related-work-map.md`
- 引用に採用する文献の `refs/summaries/*.md`

## tracked にしないもの

- raw search transcript
- web agent の一時 JSON
- 著作権上長すぎる抜粋
- 未検証の report
- 個人環境の絶対パス
