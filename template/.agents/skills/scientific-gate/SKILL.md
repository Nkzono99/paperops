---
name: scientific-gate
description: Use when judging claim readiness before Abstract, Conclusion, or main figures.
---

# scientific-gate

本文を書く前に、書いてよい主張とまだ止めるべき主張を分ける。AI に原稿を生成させる前の claim package 監査として使う。

Academic Research Skills の pipeline / integrity gate / material provenance の発想を参考にするが、paperops では `_paperops/model/research/`、`_paperops/model/research/`、`_paperops/notes/views/`、`_paperops/refs/` にあるカードとビューへ接続する。外部スキルのテンプレートや文面をコピーしない。

## 最初に読むファイル

- `_paperops/model/research/README.md`
- `_paperops/model/research/claims/`
- `_paperops/model/research/gates/`
- `_paperops/model/research/`
- `_paperops/notes/views/scientific-gate.md`
- `_paperops/notes/views/result-pattern-map.md`
- `_paperops/notes/views/claim-evidence-map.md`
- `_paperops/notes/views/assumption-ledger.md`
- `_paperops/notes/views/claim-upgrade-gates.md`
- `_paperops/notes/related-work-map.md`
- `_paperops/notes/reviewer-model.md`
- `_paperops/notes/reproducibility.md`
- `_paperops/notes/views/research-requests.md`
- `_paperops/notes/source-reach.md`
- `_paperops/refs/links.toml`
- `_paperops/refs/imports/`
- `_paperops/refs/summaries/`
- `manuscript/venue.md`
- 必要に応じて対象の figure/table、Methods、Results、Abstract、Conclusion

## Gate status

各中心主張を次のいずれかへ分類する。

- `ready-to-write`: evidence、scope、limitation、reproducibility、reader risk が揃い、本文で主張してよい。
- `analysis-needed`: 追加解析、図表、数値再計算、収束確認、統計確認が必要。
- `assumption-blocked`: 物理仮定、データ解釈、読者が突く前提を人間が承認していない。
- `supplement-only`: 本文の中心主張ではなく、補足・Methods・Data availability に回す。
- `defer`: 今回の論文では扱わない。

Abstract、Conclusion、title、main figure caption では `ready-to-write` だけを使う。中心主張が `assumption-blocked` の場合、原稿生成へ進まず、必要な確認へ戻す。`analysis-needed` でも、追加シミュレーションが投稿前に現実的かつ既存の延長線上で実施でき、期待される結果の根拠を明示できる場合だけ、`draft-predicted-results` で `% PREDICTED-RESULT:` / `% SIM-REQUEST:` 付きの予測稿を作ってよい。この場合も gate status は `analysis-needed` のままで、publish 不可、`must_not_claim`、実データ置換後の再 gate 条件を残す。

## Claim package

各 claim について、`_paperops/model/research/gates/` に gate card を作成または更新し、`_paperops/notes/views/scientific-gate.md` の claim package 表を俯瞰用に更新する。

- claim ID と claim text
- result pattern / evidence packet ID
- estimand、metric、unit of analysis、comparison
- figure/table、manuscript block
- artifact / script / input / provenance link
- 外部 bundle import state、source index / integrity manifest、source commit / dirty state、artifact category、`must_not_claim`
- central_assumptions、claim_stress_tests、external_validation_gates、path_criterion、evidence_design
- 文献・関連研究の support と反論
- independence、convergence、sensitivity、selection、negative/null case
- path-dependent claim では endpoint work、cumulative work、energy barrier、from-rest subset、force threshold。endpoint != reachability を前提にし、`W_final > 0` を release from rest の十分条件として書かない。
- evidence-design coverage。count / fraction / percentage / maximum / screening / time-correlated saved snapshots には denominator、unit of analysis、independence caveat、same denominator / same criterion、validated scope、not covered を書く。
- central assumption ledger。artifact role を measured model / validated solver output / proxy / sensitivity / authoring guard に分け、proxy や sensitivity を claim support に昇格しない。
- claim stress-test。各 claim component について stress input、stress outcome、allowed wording、must-not-claim、nearest caveat、source artifacts を書く。
- external validation needs。外部測定、文献拘束、追加 model validation が未通過の row は claim support ではなく claim upgrade blocker として扱い、Abstract / Conclusion / Key Points / main caption へ昇格させない。
- method novelty claim の direct comparator status。同じ総量、同じ物理条件、同じ estimator、同じ denominator の matched comparator が無い場合、比較表現ではなく representation scope として書く。
- run completion、final snapshot、physical equilibrium、calibrated exposure、independent snapshots の status。完了計算や最終時刻を steady state / 帯電平衡として扱わない。
- current manuscript figure set と figure role。外部 crosswalk candidate の Main Figure label は、現行本文の `includegraphics` と figure card / review response で再確認する。
- AI が転記した数値ではなく、人間または解析スクリプトで確認した数値か
- gate status と block reason
- human approval の要否と承認記録

数値、分母、単位、条件名、比較対象が不一致なら `analysis-needed` にする。時系列 snapshot、screening result、最大値、favorable condition を主要証拠に使う場合は、estimand と scope を明記する。
直接対照が未実施の方法新規性 claim、time-history の completion を equilibrium に読む claim、現行 figure set とずれた crosswalk candidate は `analysis-needed` または `assumption-blocked` にする。
method sanity、workflow QA、readiness table、overclaim consistency audit、condition matrix、claim stress-test、external validation needs は、存在しても full numerical verification や review closure ではない。

## 手順

1. 対象範囲を決める。Abstract / Conclusion / central claim / figure story / section claim のどれを gate するか明記する。
2. `_paperops/model/research/` と `_paperops/notes/views/result-pattern-map.md` から claim に昇格しようとしている evidence packet を確認する。raw result を直接 claim にしない。
3. `_paperops/model/research/claims/` と `_paperops/notes/views/claim-evidence-map.md` の status と矛盾していないか確認する。
4. `_paperops/notes/reproducibility.md`、`_paperops/refs/links.toml`、`_paperops/refs/imports/`、`_paperops/notes/source-reach.md` から provenance と再現可能性を確認する。外部 bundle 由来の evidence は `make external-import-check` の warning を確認する。
5. `_paperops/notes/related-work-map.md` と `_paperops/refs/summaries/` から関連研究、反論、引用可能な support を確認する。
6. 各 claim を gate status へ分類し、gate card に block reason と次の route を書く。
7. central assumptions、claim stress tests、external validation gates がある場合は、`_paperops/notes/views/assumption-ledger.md` と `_paperops/notes/views/claim-upgrade-gates.md` にも俯瞰用の row を残す。
8. `ready-to-write` の claim だけ、本文や caption で使える scope statement を作る。
9. `analysis-needed` のうち追加シミュレーションが現実的な claim は、Future Work や defensive prose に逃がさず `draft-predicted-results` へ渡す候補にする。予測稿は `% PREDICTED-RESULT:` comment、analysis request、`xx` 置換条件、再 gate 条件を必ず持つ。
10. 人間承認が必要な assumption は、AI が勝手に受容せず gate card と `_paperops/notes/views/scientific-gate.md` の approval log に残す。

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
- `Allowed wording / must-not-claim`
- `Assumption ledger updates`
- `Claim stress-test / external validation gate updates`
- `Assumption approvals needed`
- `Routes`: `/map-result-patterns`、`/research-related-work`、`/source-reach-scan`、`/calibrate-claims`、`/figure-story-audit`、`/draft-predicted-results`、`/peer-review-manuscript`、`_paperops/model/issues/analysis/`
- `Files updated`
- `Checks run`

## Codex 実行メモ

- ユーザーが明示しない限り、本文を書き換えない。
- `_paperops/refs/` と `_paperops/notes/` の作業用ドキュメントは日本語で書く。
- 既存 source の DOI、metadata、投稿日、投稿先 policy、外部 repository の軽い確認は必要なら web で行い、出典リンクを残す。新規 source channel、credential、raw capture、SNS / 動画 / platform-specific source が絡む場合は先に `/source-reach-scan` へ戻す。
- `assumption-blocked` を文章上の hedge だけで処理しない。承認または scope 変更へ戻す。
- `analysis-needed` を最終 prose に見せない。予測稿が必要なら `draft-predicted-results` を使い、`PREDICTED-RESULT` comment と `_paperops/model/issues/analysis/` への接続を残す。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
