# refs/source-reach

外部 Web、GitHub、動画、RSS、SNS、議論サイトなどの raw capture と到達経路メモを置く一時領域。

paperops では raw 外部データを正本にしない。正本は、確認済みの要約を置く `notes/source-reach.md`、関連研究の議論を置く `notes/related-work-map.md`、引用に採用する `refs/summaries/` と `.bib`、再現性に関係する `notes/reproducibility.md` である。

## 推奨構造

```text
refs/source-reach/<topic-slug>/
  route.toml            # channel、preferred route、fallback、credential need
  discussion.md         # 人間が確認して整理した調査メモ
  raw/                  # raw search result / transcript / dump。既定では Git 管理しない
  doctor.generated.json # agent-reach 等の診断結果。既定では Git 管理しない
```

## tracked にするもの

- route の意図を共有する `route.toml`
- 人間が確認して短く整理した `discussion.md`
- 論文に採用する finding を昇格した `notes/source-reach.md`

## tracked にしないもの

- raw HTML、SNS dump、長い transcript
- cookie、token、個人アカウント情報
- 未検証の自動レポート
- 著作権上長すぎる抜粋
- 個人環境の絶対パス
