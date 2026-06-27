---
name: design-paper-figure
description: Use when creating or revising an individual manuscript figure, figure panel, table-like visual, runops plot request, or caption from data or an existing plot.
---

# design-paper-figure

論文図を「データがあるから図にする」ものではなく、読者にさせる比較・判断から設計する。`plan-figure-story` は必要な図を決める入口であり、この skill は採用済みまたは作成予定の figure / panel を reader-facing artifact へ設計するために使う。

## 最初に読むファイル

- `_paperops/claims/claims/`
- `_paperops/evidence/results/`
- `_paperops/evidence/figures/`
- `_paperops/notes/views/storyline.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/condition-context-map.md`
- `_paperops/refs/links.toml`
- `_paperops/requests/analysis/`
- 対象 figure / table、caption、参照する本文 block
- runops など外部生成元がある場合は import state と request card

## Figure design brief

figure card に、少なくとも次を残す。

```yaml
design_review:
  reader_task: unchecked
  takeaway_sentence: unchecked
  claim_or_decision: unchecked
  encoding_choice: unchecked
  scale_and_denominator: unchecked
  uncertainty_or_distribution: unchecked
  annotation_caption: unchecked
  color_accessibility: unchecked
  runops_handoff: unchecked
  acceptance_criteria: unchecked
```

```text
reader_task:
takeaway_sentence:
claim_or_decision:
why_this_figure_not_text_or_table:
panel_story:
primary_comparison:
encoding_choice:
scale_and_denominator:
uncertainty_or_distribution:
annotation_plan:
caption_plan:
color_accessibility:
render_size:
runops_handoff:
acceptance_criteria:
```

## 手順

1. `reader_task` を一文で書く。読者が比較するのか、境界を見つけるのか、例外を確認するのか、機構を追うのかを分ける。
2. `takeaway_sentence` を一文で書く。caption や本文が最終的に言うことより強くしない。
3. `claim_or_decision` を claim card、result card、visual obligation、analysis request のいずれかに接続する。データがあるから図にしない。
4. `why_this_figure_not_text_or_table` を確認する。少数の数値だけなら本文または table、空間状態・分布・境界・階層なら figure を優先する。
5. panel を持つ図では `panel_story` を書く。各 panel が同じ reader_task に寄与しないなら、図を分けるか supplement へ送る。
6. graphical perception を意識し、主要比較はできるだけ共通軸上の位置で読ませる。面積、3D 効果、二軸、過密 color encoding は、読者タスクに必須でない限り避ける。
7. 平均値だけの bar / line に逃げず、n、denominator、分布、uncertainty_or_distribution、scope を必要に応じて見せる。隠れる distribution が claim に効くなら summary-only 図にしない。
8. scale、zero、normalization、denominator、binning、sample fraction、unit_of_analysis を `scale_and_denominator` に書く。比較図では同じ scale / denominator で読めるかを確認する。
9. heatmap / colormap は perceptually ordered で、color_accessibility と color-bin saturation を確認する。rainbow 的な順序誤読、色覚多様性、print 時の劣化を避ける。
10. annotation_plan と caption_plan を図の一部として扱う。caption は run list ではなく、図が支える contrast、boundary、mechanism、not-claiming を先に言う。
11. final size で読めるかを確認する。axis label、legend、panel label、line width、marker size、caption との重複を点検する。
12. runops_handoff が必要なら `_paperops/requests/analysis/` に、plot recipe ではなく reader_task、takeaway_sentence、source data、required panels、public labels、denominator、export format、acceptance_criteria を渡す。
13. rendered output を見て、acceptance_criteria を満たさない場合は「使える図」として採用しない。figure card の route を manuscript / result-card / claim-card / analysis-request / supplement / discard に戻す。

## Runops handoff 最小形

```text
runops_handoff:
- target_link:
- requested_output:
- source_data:
- reader_task:
- takeaway_sentence:
- required_panels:
- public_labels:
- denominator_and_units:
- export_format: pdf/svg/png with final-size raster preview
- acceptance_criteria:
```

## 出力

- 更新済み figure card の Figure design brief
- panel_story と main / supplement 判断
- caption rewrite plan
- runops_handoff / analysis request draft
- acceptance_criteria と採否判断
- 必要なら `figure-story-audit` に渡す監査メモ

## Codex 実行メモ

- 既存 plot をそのまま採用しない。まず reader_task と takeaway_sentence を書く。
- runops で作られた図でも、paper 側の claim、caption、denominator、public label に合わなければ analysis request へ戻す。
- `plan-figure-story` の visual obligation と、`figure-story-audit` の denominator / caption /本文参照監査の間をつなぐ。
- 図中に内部 run label、target label、作業用略語が残る場合は public label map または request card に戻す。
