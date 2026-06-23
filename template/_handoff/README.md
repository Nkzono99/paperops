# _handoff

人間から AI へ渡す未整理ファイルの一時受け取り箱。

ここには、スクリーンショット、PDF、メモ、外部ツールの出力、共同研究者から届いたファイルなど、まだ置き場所が決まっていないものを雑多に入れてよい。内容は既定で Git 管理しない。

AI はこのディレクトリを見たら、必要に応じて以下へ整理する:

- 文献や参照知識: `refs/summaries/`、`refs/links.toml`
- ローカルパスや外部ディレクトリ: `refs/local/locations.toml`
- 追加解析・図表・実験要望: `requests/analysis/`、`requests/writing/`、俯瞰は `notes/views/research-requests.md`
- セッション引き継ぎや作業メモ: `notes/handoff.md`、`notes/todo.md`
- 再現性や公開可能な provenance: `notes/reproducibility.md`

秘密情報、未公開データ、個人環境の絶対パスは tracked ファイルへ移さず、共有できる要約や link intent だけを残す。

`refs/` と `notes/` に整理する作業用ドキュメントは日本語で書く。citation key、field name、外部ツール名などの識別子だけは英語のままでよい。
