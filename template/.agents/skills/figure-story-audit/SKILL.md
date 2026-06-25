---
name: figure-story-audit
description: Use when checking whether figures support claims, evidence, captions, and text references.
---

# figure-story-audit

図表を結果の置き場ではなく、主張を支える証拠として監査する。

## 最初に読むファイル

- `notes/views/result-pattern-map.md`
- `notes/views/claim-evidence-map.md`
- `notes/views/condition-context-map.md`
- `claims/gates/`
- 対象の figure/table caption
- caption を参照する本文 block
- `notes/reproducibility.md`

## 手順

1. 各 figure/table について、対応する result pattern / evidence packet、figure claim、panel evidence、boundary、uncertainty を整理する。
2. condition axis、public denominator、panel role を整理する。
3. 本文参照が figure の takeaway と一致しているか確認する。
4. caption が run/case list ではなく、図が支える contrast、mechanism、boundary を先に言っているか確認する。
5. caption に sample/condition/scope/statistics が不足していないか確認する。
6. fraction / count / percentage / sample / onset / majority / maximum / best / worst を含む場合、same denominator、independence caveat、max-comparison の criterion、verification coverage を確認する。比較が envelope、screening maxima、exploratory extrema なら main claim の controlled comparison として扱わない。
7. release / detachment / ejection / lofting の figure では endpoint != reachability を確認する。endpoint work、cumulative work、energy barrier、from-rest subset、force threshold crossing、energy-equivalent speed を分け、caption が from-rest proof や actual trajectory speed に読ませていないか見る。
8. representation / state-variable claim では state variable visualized を確認する。surface state、field map、microstructure、charge distribution、source attribution などに依存する claim は、outcome-only figure risk と state visualization is not comparator を figure card に明記する。
9. representative / example / diagnostic curve を置く場合、その曲線が統計の denominator source なのか、criterion visualization なのかを分ける。複数 condition から選んだ例は diagnostic-only、not denominator source、not condition ranking を caption に出す。
10. heatmap / phase-space / color map の場合、主張を運ぶ visual contrast、W=0 などの decision boundary、critical threshold、color-bin saturation、denominator を確認する。ほぼ同色で境界が読めない場合は、boundary curve、threshold table、criterion hierarchy、signed-work profile への差し替えを検討する。
11. main-text figure は caption だけでなく本文側から `\ref{fig:...}` / `\autoref{fig:...}` / `\cref{fig:...}` で narrative に接続されているか確認する。
12. claim-to-figure crosswalk や外部 candidate display を読む場合、required artifact の存在と current manuscript role は別 status として扱う。現行 `includegraphics`、figure role note、review response が main / supplement / notes-only を上書きしている場合は `stale_main_figure_candidate` として扱い、claim promotion を止める。
13. `notes/views/result-pattern-map.md` の packet、`notes/views/claim-evidence-map.md` の Figure/table 欄、必要なら `notes/views/condition-context-map.md` を更新する。
14. 図表 provenance が必要なら `notes/reproducibility.md` に追記する。

## 出力

- Figure/table story map
- Result pattern / evidence packet map
- Condition axis / public denominator map
- Path criterion map
- State visualization / outcome-only risk
- Denominator / independence / max-comparison / verification coverage warnings
- Caption rewrite plan
- Body reference fixes
- Claim-evidence map updates
- Reproducibility updates

## Codex 実行メモ

- `notes/views/claim-evidence-map.md` と caption/本文参照を照合する。
- caption が claim, evidence, boundary を示しているか確認する。
- saturated heatmap や hidden threshold を主図証拠として通さない。
- endpoint work、cumulative work、energy barrier、same denominator、independence caveat、diagnostic-only の扱いを確認する。
- state variable visualized、outcome-only figure risk、state visualization is not comparator を figure card に残す。
- `make figure-reference-check` を使い、main-text figure label が本文から参照されているか確認する。
- provenance が変わる場合は `notes/reproducibility.md` を更新する。
