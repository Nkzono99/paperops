# requests 層

`_paperops/requests/` は paper 側から発生した追加解析、図表、文献、改稿の依頼をカード化する層である。

- `analysis/`: runops project や解析コードへ戻す追加解析・再計算・図表生成依頼。
- `writing/`: claim / feedback / gate に基づく原稿 block の改稿依頼。

原稿へのフィードバックが本文だけで解決できない場合、AI は feedback card から request card を作り、実行後に関連 card と manuscript block へ戻す。
