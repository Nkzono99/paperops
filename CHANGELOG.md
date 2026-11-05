# Changelog

## 2.1.0（未リリース）

- 結果がまだ無い所を、根拠のある予想で先に書けるようにした。論文全体の流れを結果が揃う前に確かめ、
  あとから計算で答え合わせをする進め方のため。
  - skill `paper-predict` を追加: 予想の立て方（根拠、確信度、いまの simulator で得られるかの見積もり、
    外れた場合）、検証の順番、結果が出たときの答え合わせ。
  - `BRIEF.md` の発見に `状態`（`確認済み` / `予想` / `一部確認`）、`確かめ方`、`外れたら` を持たせ、
    「検証の順番」の節を足した。主張が予想に依るときは、外れても言える主張を添える。
  - 本文と `numbers.tex` の予想は `\pred{}` で印を付ける（PDF で色が付く）。雛形の preamble に定義を追加。
  - 予想の図は `make.py` の `predict()` に根拠を code で書き、`common.mark_predicted()` で印を入れる。
    `figure.md` の状態に `predicted` を追加。
  - `pops context` が、発見ごとの状態と、原稿に残っている `\pred` の数を表示する。
- skill と README の例を、著者の研究分野と重ならない題材（管の流れ）に替えた。実在の結果と食い違う例が
  エージェントの予想を引っ張らないようにするため。
- 2.0.0 で作った project は、`pops update` のあと、preamble に `\pred` の定義を足す（`paper-predict` に記載）。

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
