# Codex harness

このディレクトリは Codex 用のプロジェクトローカル skill 入口を提供する。

`template/.claude/skills/` をハーネス方針の source of truth とし、`.agents/skills/` は Codex が同じ作業フローを発見するための薄い互換層として維持する。Claude 固有の `allowed-tools` や slash command 前提は、Codex の利用可能な tool と `AGENTS.md` のルールに読み替える。

互換層を更新する場合は、対応する `.claude/skills/<skill>/SKILL.md` との差分を小さく保ち、片方だけに恒久的な方針を追加しない。
