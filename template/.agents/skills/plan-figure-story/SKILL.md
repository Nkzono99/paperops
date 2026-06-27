---
name: plan-figure-story
description: Use before drafting Results or locking ARCHITECTURE_LOCKED, to design required figures and detect missing visual obligations from claims and available artifacts.
---

# plan-figure-story

本文を書く前に、中心 claim を読者が理解するための図表構成を設計する。`figure-story-audit` は既存図の監査であり、この skill は **absence is invisible** 問題、つまり存在しないが必要な図を先に発見するために使う。

## 最初に読むファイル

- `_paperops/defaults/contracts/figures.yml`
- `_paperops/contracts/figures.yml` if project overlay exists
- `manuscript/writing-profile.yml`
- `_paperops/claims/claims/`
- `_paperops/claims/gates/`
- `_paperops/evidence/results/`
- `_paperops/evidence/figures/`
- `_paperops/refs/links.toml`
- `_paperops/refs/imports/`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/condition-context-map.md`
- `_paperops/notes/reproducibility.md`
- 既存の `manuscript/*/sections/*results*.tex` と caption

## 手順

1. 中心 claim ごとに、文章だけでは読者が理解できない要素を `visual_obligations` として列挙する。
2. `_paperops/defaults/contracts/figures.yml`、必要な `_paperops/contracts/figures.yml` overlay、`manuscript/writing-profile.yml` を重ね、paper type が要求する role を確認する。
3. computational modeling では、空間分解された状態量が新規性の入口なら `model_or_state_visualization`、経路依存推定量や threshold が claim を支えるなら `estimator_or_decision_criterion` を原則 required にする。
4. 利用可能な result、figure data、linked artifact、既存 plot script を確認し、採用候補を `.paperops/cache/figure-candidates.yml` に一時整理する。生成物なので Git 管理しない。
5. 採用する図だけを `_paperops/evidence/figures/` の figure card に昇格し、`satisfies_visual_obligations` に対応する `VO-*` ID を記録する。
   その後、個別の図や panel を作る前に `design-paper-figure` で reader_task、takeaway_sentence、encoding_choice、scale_and_denominator、runops handoff、acceptance criteria を固定する。
6. claim card には `visual_obligations` を残す。図が不要な claim は `no_figure_reason` を明示する。
7. 主図と補足図の切り分けを決める。sensitivity / screening 図は、中心 claim を読むための前提でなければ supplement を既定にする。
8. Figure 1 は、paper type 契約と reader question に照らして決める。model/state が新規性の入口なら、heterogeneous screening summary を Figure 1 にしない。
9. `make figure-obligation-check` を実行し、`ARCHITECTURE_LOCKED` の前に `visual_obligations_satisfied` の根拠を作る。

## Visual obligation の最小形

claim card:

```yaml
visual_obligations:
  - id: VO-STATE-0001
    role: model_or_state_visualization
    required: true
    visual_object: "3D surface potential and target geometry"
    main_or_supplement: main
    missing_action: generate_figure
no_figure_reason: ""
```

figure card:

```yaml
satisfies_visual_obligations:
  - VO-STATE-0001
current_manuscript_role: main
```

## 出力

- Figure role plan
- Claim -> visual obligation crosswalk
- Missing figure / missing_action list
- Main vs supplement decision
- Figure 1 role decision
- `.paperops/cache/figure-candidates.yml` if useful
- 更新済み claim / figure card
- `design-paper-figure` に渡す figure / panel design backlog
- `figure-obligation-check` 結果

## Codex 実行メモ

- 原稿本文を先に書かない。本文生成前に図の role と obligation を固定する。
- 既存図だけを正当化しない。中心 claim から逆算して、state_visualization、criterion_curve、primary_evidence、mechanism_or_boundary_comparison の欠落を見る。
- 図の存在が決まっただけで採用しない。実際の plot、panel、caption、runops request は `design-paper-figure` で読者タスクから設計してから使う。
- max / p95 / fraction / sample count を主図で使う場合は、同じ denominator、unit of analysis、independence caveat を `figure-story-audit` に引き継ぐ。
- figure candidate は `.paperops/cache/` の生成一時物に置き、採用図だけを card 化する。
