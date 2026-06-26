# project workflow state and overlays

`_paperops/workflow/` は project-owned の workflow state と overlay を置く場所である。

- `machine.yml`: project 固有に状態機械を上書きする場合だけ置く。通常は `_paperops/defaults/workflow/machine.yml` を読む。
- `current-state.yml`: 現在の全体状態、section 状態、依存 artifact、guard 達成状況。
- `round-summary.yml`: 現在の reviewer loop の要約。
- `decisions.yml`: 人間が行った重要判断。
- `focus-policy.yml`: project 固有に focus policy を上書きする場合だけ置く。通常は `_paperops/defaults/workflow/focus-policy.yml` を読む。
- `subagent-roster.yml`: project 固有に subagent roster を上書きする場合だけ置く。通常は `_paperops/defaults/workflow/subagent-roster.yml` を読む。

逐次ログ、stale map、context pack は `.paperops/cache/` に置き、Git 管理しない。本文を書き換える前に、`pops workflow status` と `pops workflow next` で戻る深さを確認する。
