# Changelog

## 2.0.0（2026-11-05）

最小限の構成への作り直し。1.x とは互換性がない。

- 論文 project を `BRIEF.md`（何を言う論文か）、`STYLE.md`（添削から学んだ書き方）、`manuscript/`、
  `figures/<name>/`、`paper.toml`、`LOG.md` だけで構成する。
- コマンドを `pops init` / `update` / `context` / `outline` / `build` の 5 個にした。実行時の依存は無い。
- skill を `paper-brief` / `paper-draft` / `paper-figure` / `paper-revise` / `paper-check` の 5 個にした。
- 添削は TeX の `%>` コメントで受け、反映後に同種の箇所へ広げ、好みを STYLE の規則として残す。
  論文をまたぐ好みは共有 STYLE（既定 `~/.config/paperops/STYLE.md`）に置く。
- 図は `figure.md` にメッセージを書き、掲載寸法の描画結果を見て直す round を記録する。
- 主張が伝わるかを、主張を知らない別のエージェントに PDF だけを読ませて確かめる。
- `paper.toml` の `[[sources]]` で runops project を参照し、`pops context` が解析 topic の README を一覧する。
- 削除: 六つの typed model（`_paperops/`）、`pops change` / `compile` / `write` / `workflow` / `model` /
  `scratch` / `doctor` / `links`、section contract と各種 check script、日英 block の同期管理、
  再利用 workflow、49 個の skill。1.x の project は `paper-harness-cli==1.0.0` で使い続けられる。

## 1.0.0 以前

tag `v1.0.0` とそれ以前の履歴を参照。
