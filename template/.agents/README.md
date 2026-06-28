# Codex harness

このディレクトリは Codex 用のプロジェクトローカル skill 入口を提供する。

`.agents/skills/` を共通手順の source of truth とし、`.claude/skills/` は Claude Code 用 wrapper として `.agents/skills/<skill>/SKILL.md` を読む。Claude 固有の `allowed-tools` や slash command 前提は wrapper 側に閉じ、恒久的な執筆方針は `.agents/skills/` 側へ置く。

wrapper を更新する場合は、対応する `.agents/skills/<skill>/SKILL.md` への参照を保ち、片方だけに恒久的な方針を追加しない。
