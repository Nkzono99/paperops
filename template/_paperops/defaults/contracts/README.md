# managed default contracts

`_paperops/defaults/contracts/` は paperops-managed の標準 contract を置く場所である。

ここにある file は `pops update-paperops` の managed update 対象であり、project repo では通常編集しない。論文固有の上書きが必要な場合は `_paperops/contracts/` に同名 file を置く。

skill や agent entrypoint はここには置かない。Codex / Claude Code が自然に読む入口は `.agents/skills/` と `.claude/skills/` に残す。
