---
name: contextualize-conditions
description: Use when translating run conditions into claim scope, boundaries, or figure story.
---

# contextualize-conditions

AI 初稿や Results / Discussion に出てくる `12 条件中 2 条件`、`8 条件中 0 条件`、run inventory、case list を、読者に意味のある論文文脈へ翻訳する。

## 最初に読むファイル

- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/condition-context-map.md`
- `_paperops/notes/views/argument-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/evidence/results/`
- `_paperops/claims/claims/`
- `_paperops/notes/reviewer-model.md`
- `_paperops/notes/reproducibility.md`
- 対象の Results / Discussion / figure captions

## 目的

- 条件数を claim ではなく evidence metadata として扱う。
- local ID、case count、screening 結果を、`core evidence`、`mechanism`、`boundary`、`robustness`、`negative control`、`exploratory`、`provenance-only` に分類する。
- 0 条件や少数条件を、単なる失敗ではなく、negative evidence、境界条件、不十分な coverage のどれかへ分類する。
- defense hedge ではなく、scope qualifier として本文へ戻す。
- denominator の意味を `_paperops/notes/views/condition-context-map.md` と `_paperops/notes/reproducibility.md` に残す。

## 手順

1. `_paperops/notes/views/result-pattern-map.md` があれば、先に pattern ID と observed contrast を確認する。対象本文から直接抜く場合も、local condition、case count、run inventory、condition label を claim ではなく result pattern の一部として扱う。
2. 各 count の denominator が何を意味するか確認する。読者に意味がない denominator は本文の主張から外す。
3. 各 condition group を claim role に分類する。
4. 本文で使う公開条件名と、notes / supplement に退避する provenance を分ける。
5. `_paperops/notes/views/condition-context-map.md` の対応表を更新する。
6. 必要に応じて `_paperops/evidence/results/` の result card、`_paperops/claims/claims/` の scope / limitation、`_paperops/notes/views/result-pattern-map.md`、`_paperops/notes/views/claim-evidence-map.md`、`_paperops/notes/reproducibility.md` の条件集合・選別フローを更新する。
7. 本文を編集する場合は、条件数ではなく、物理条件、対照、境界条件、機構を主語にする。

## 変換例

- Before: `12 条件中 2 条件で正の work が残った。`
- After: `局所保持が target の下向き領域に集中する境界条件でだけ release-work bracket が残り、同じ電荷量でも支持粒子側や広域緩和では消えた。`

- Before: `8 条件中 0 条件であった。`
- After: `この対照は、単なる総電荷量ではなく空間配置と保持範囲が必要条件であることを示す negative evidence として扱う。`

## 出力

- `Condition abstraction map`
- `Count-led sentences`
- `Paper-context wording`
- `Move to Methods/Supplement/notes`
- `Claim scope updates`
- `Risks of over-abstraction`

## Codex 実行メモ

- `_paperops/refs/` と `_paperops/notes/` の作業用ドキュメントは日本語で書く。
- 条件数を消しすぎて透明性を失わない。denominator は必要なら Methods、caption、supplement、`_paperops/notes/reproducibility.md` に残す。
- 過度な抽象化で overclaim しない。抽象化後の主張は claim card と `claim-evidence` view の scope / limitation に接続する。
