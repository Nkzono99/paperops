# managed default workflow

`_paperops/defaults/workflow/` は paperops-managed の標準 workflow machine、focus policy、subagent roster を置く場所である。

ここにある file は `pops update-paperops` の managed update 対象であり、project repo では通常編集しない。現在状態、review round summary、人間判断は `_paperops/workflow/` に置く。

skill や agent entrypoint はここには置かない。Codex / Claude Code が自然に読む入口は `.agents/skills/` と `.claude/skills/` に残す。
