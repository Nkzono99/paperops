---
name: scientific-gate
description: Use when judging claim readiness before Abstract, Conclusion, or main figures.
---

# scientific-gate

本文を書く前に、書いてよい主張とまだ止めるべき主張を分ける。AI に原稿を生成させる前の claim package 監査として使う。

Academic Research Skills の pipeline / integrity gate / material provenance の発想を参考にするが、paperops では `claims/`、`evidence/`、`notes/views/`、`refs/` にあるカードとビューへ接続する。外部スキルのテンプレートや文面をコピーしない。

## 最初に読むファイル

- `claims/README.md`
- `claims/claims/`
- `claims/gates/`
- `evidence/`
- `notes/views/scientific-gate.md`
- `notes/views/result-pattern-map.md`
- `notes/views/claim-evidence-map.md`
- `notes/related-work-map.md`
- `notes/reviewer-model.md`
- `notes/reproducibility.md`
- `notes/views/research-requests.md`
- `notes/source-reach.md`
- `refs/links.toml`
- `refs/imports/`
- `refs/summaries/`
- `manuscript/venue.md`
- 必要に応じて対象の figure/table、Methods、Results、Abstract、Conclusion

## Gate status

各中心主張を次のいずれかへ分類する。

- `ready-to-write`: evidence、scope、limitation、reproducibility、reader risk が揃い、本文で主張してよい。
- `analysis-needed`: 追加解析、図表、数値再計算、収束確認、統計確認が必要。
- `assumption-blocked`: 物理仮定、データ解釈、読者が突く前提を人間が承認していない。
- `supplement-only`: 本文の中心主張ではなく、補足・Methods・Data availability に回す。
- `defer`: 今回の論文では扱わない。

Abstract、Conclusion、title、main figure caption では `ready-to-write` だけを使う。中心主張が `analysis-needed` または `assumption-blocked` の場合、原稿生成へ進まず、必要な確認へ戻す。

## Claim package

各 claim について、`claims/gates/` に gate card を作成または更新し、`notes/views/scientific-gate.md` の claim package 表を俯瞰用に更新する。

- claim ID と claim text
- result pattern / evidence packet ID
- estimand、metric、unit of analysis、comparison
- figure/table、manuscript block
- artifact / script / input / provenance link
- 外部 bundle import state、source index / integrity manifest、source commit / dirty state、artifact category、`must_not_claim`
- 文献・関連研究の support と反論
- independence、convergence、sensitivity、selection、negative/null case
- method novelty claim の direct comparator status。同じ総量、同じ物理条件、同じ estimator、同じ denominator の matched comparator が無い場合、比較表現ではなく representation scope として書く。
- run completion、final snapshot、physical equilibrium、calibrated exposure、independent snapshots の status。完了計算や最終時刻を steady state / 帯電平衡として扱わない。
- current manuscript figure set と figure role。外部 crosswalk candidate の Main Figure label は、現行本文の `includegraphics` と figure card / review response で再確認する。
- AI が転記した数値ではなく、人間または解析スクリプトで確認した数値か
- gate status と block reason
- human approval の要否と承認記録

数値、分母、単位、条件名、比較対象が不一致なら `analysis-needed` にする。時系列 snapshot、screening result、最大値、favorable condition を主要証拠に使う場合は、estimand と scope を明記する。
直接対照が未実施の方法新規性 claim、time-history の completion を equilibrium に読む claim、現行 figure set とずれた crosswalk candidate は `analysis-needed` または `assumption-blocked` にする。

## 手順

1. 対象範囲を決める。Abstract / Conclusion / central claim / figure story / section claim のどれを gate するか明記する。
2. `evidence/` と `notes/views/result-pattern-map.md` から claim に昇格しようとしている evidence packet を確認する。raw result を直接 claim にしない。
3. `claims/claims/` と `notes/views/claim-evidence-map.md` の status と矛盾していないか確認する。
4. `notes/reproducibility.md`、`refs/links.toml`、`refs/imports/`、`notes/source-reach.md` から provenance と再現可能性を確認する。外部 bundle 由来の evidence は `make external-import-check` の warning を確認する。
5. `notes/related-work-map.md` と `refs/summaries/` から関連研究、反論、引用可能な support を確認する。
6. 各 claim を gate status へ分類し、gate card に block reason と次の route を書く。
7. `ready-to-write` の claim だけ、本文や caption で使える scope statement を作る。
8. 人間承認が必要な assumption は、AI が勝手に受容せず gate card と `notes/views/scientific-gate.md` の approval log に残す。

## Role pass

一人の agent 内でも、次の順番を分けて考える。

- `Analyst`: raw result から result pattern / evidence packet を確認する。文章を磨かない。
- `Numerical reviewer`: 分母、単位、比較条件、収束、独立性、感度、再計算可能性を見る。
- `Skeptical reviewer`: 最も強い反論、代替説明、読者が突く assumption を出す。
- `Human approval checkpoint`: 中心主張と assumption を人間判断に戻す箇所を明示する。
- `Writer`: `ready-to-write` だけを本文へ渡す。

## 出力

- `Gate scope`
- `Claim readiness table`
- `Blocking issues`
- `Approved writing scope`
- `Assumption approvals needed`
- `Routes`: `/map-result-patterns`、`/research-related-work`、`/source-reach-scan`、`/calibrate-claims`、`/figure-story-audit`、`/peer-review-manuscript`、`requests/analysis/`
- `Files updated`
- `Checks run`

## Codex 実行メモ

- ユーザーが明示しない限り、本文を書き換えない。
- `refs/` と `notes/` の作業用ドキュメントは日本語で書く。
- 既存 source の DOI、metadata、投稿日、投稿先 policy、外部 repository の軽い確認は必要なら web で行い、出典リンクを残す。新規 source channel、credential、raw capture、SNS / 動画 / platform-specific source が絡む場合は先に `/source-reach-scan` へ戻す。
- `assumption-blocked` を文章上の hedge だけで処理しない。承認または scope 変更へ戻す。
