# workflow

`workflow/` は、論文執筆を直列パイプラインではなく、階層型状態機械と成果物依存で扱うための層である。

- `machine.yml`: 固定の全体状態、section 状態、issue class、transition guard、loop policy。
- `current-state.yml`: 現在の全体状態、section 状態、依存 artifact、guard 達成状況。
- `round-summary.yml`: 現在の reviewer loop の要約。
- `decisions.yml`: 人間が行った重要判断。

逐次ログ、stale map、context pack は `.paperops/cache/` に置き、Git 管理しない。本文を書き換える前に、`pops workflow status` と `pops workflow next` で戻る深さを確認する。
