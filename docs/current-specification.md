# paperops current specification index

この文書は現行仕様の正本ではなく、正本文書への索引である。古い「現行仕様書」は `architecture.md`、`cli.md`、migration docs、各 skill との重複が大きくなり、Agent が stale な説明を正本として読んでしまうリスクがあったため、ここでは入口と不変条件だけを管理する。

詳細がこの文書と食い違う場合は、下表の source of truth を優先する。

| scope | source of truth | note |
| --- | --- | --- |
| architecture / layer contract | `docs/architecture.md` | root 層、下流論文層、`_paperops/`、`paper_ir`、workflow state、submission axis |
| CLI behavior | `docs/cli.md`, `src/paperops/cli/` | `pops init`、`pops update-paperops`、`pops scratch`、`pops workflow` |
| migrations | `docs/migrations/` | 下流互換、legacy path、overlay migration |
| release and distribution | `docs/distribution.md`, `docs/release.md`, `CHANGELOG.md` | package / tag / PyPI / scaffold version |
| skill routing | `docs/skill-catalog.md`, `template/.agents/skills/*/SKILL.md` | `.agents/skills/` が共通手順の source of truth |
| Claude Code wrappers | `template/.claude/skills/*/SKILL.md`, `template/scripts/check-skill-mirror.py` | wrapper は `.agents` source を import する互換入口 |
| downstream user interface | `template/README.md`, `template/AGENTS.md`, `template/CLAUDE.md` | 下流 project に配布される操作入口 |

## Current Invariants

- root repository はテンプレート管理層であり、`template/` は下流論文 project に配布される scaffold である。
- 下流作成は `pops init` を正道とする。下流の project-owned extension は `AGENTS.project.md`、`CLAUDE.project.md`、`Makefile.project` に置く。
- 人間が普段触る入口は `story/`、`manuscript/`、`submission/`、review comments である。
- AI / harness が使う internal state は `_paperops/` に置く。旧 top-level `notes/`、`refs/`、`claims/`、`evidence/` などは互換読み取り対象に留める。
- `paper_ir` と section plan は生成一時物であり、必要な場合だけ `.paperops/cache/` に置く。
- `manuscript/` は living manuscript / authoring source であり、投稿後や査読後も編集してよい。
- `submission/` は submission candidate、round snapshot、submitted / under-review / revision-candidate の証跡を置く派生層である。
- `submission-gate` は authoring source から submission candidate へ切る前の strict gate であり、`check-predicted-results.py`、authoring intent、open AREQ、submission drift を確認する。

## Authoring And Submission Axis

投稿前に原稿を完全な公開物として扱いすぎると、追加シミュレーションで解ける不定性を Future Work や defensive prose に逃がしやすい。そのため authoring axis と submission axis を分ける。

| axis | state examples | managed by |
| --- | --- | --- |
| authoring | `authoring`, `prediction-staged`, `executed`, `reconciled`, `revision-authoring` | `manuscript/`, `_paperops/requests/analysis/`, workflow state |
| submission | `candidate`, `gated`, `frozen`, `submitted`, `under-review`, `revision-candidate`, `resubmitted` | `submission/`, `_paperops/workflow/submission-ledger.yml`, `submission-gate` |

`draft-predicted-results` は、投稿前に実施可能で予測根拠がある追加解析を、`PREDICTED-RESULT`、`SIM-REQUEST`、`EXPECTATION-BASIS`、`REPLACE-XX`、`xx` placeholder と `_paperops/requests/analysis/` の request card へ接続した予測稿として authoring source に置く。submission candidate には予測稿、open AREQ、`xx` を残さない。

## Manuscript Architecture Routes

原稿完成の route-level skill は `finish-manuscript` である。これは writer ではなく orchestrator として動き、必要に応じて次の specialist skill を呼ぶ。

| route | purpose |
| --- | --- |
| `design-paper-storyline` | story spine、Results hierarchy、Discussion functions、reader promise を固定する |
| `plan-figure-story` | claim から visual obligation と main / supplement split を決める |
| `design-paper-figure` | 個別図の図の設計意図、reader task、takeaway、encoding、scale / denominator、caption、runops handoff、acceptance criteria を固定する |
| `compile-results-section` | reader question -> answer -> evidence -> figure -> comparator -> consequence の順序へ変換する |
| `compile-discussion-section` | observation、inference、mechanism、alternative、implication、prediction、limitation を分ける |
| `review-block-flow` | DRAFTED section を AUDITED に進める前に block operation table で author stance、reader question、why here、move / split / merge / delete / add を確認する |
| `finalize-manuscript` | Finish criteria、human approval、`make finish-manuscript-check`、submission handoff を確認する |

## References And Bibliography

標準の `.bib` は `manuscript/shared/bib/` に置く。外部 import や curated source は `_paperops/refs/bib/curated/` と `_paperops/refs/bib/imported/` を使う。legacy `refs/bib/` は互換読み取り対象であり、新規 scaffold の正道ではない。

`lint-bib.py`、`check-citations.py`、submission build helper の実際の探索順が CLI / script 挙動の正本である。

## Update Rule

この索引へ詳細仕様を追加しない。新しい挙動を導入する場合は、次の順で更新する。

1. 実体の script / CLI / skill / template file を更新する。
2. `docs/architecture.md`、`docs/cli.md`、`docs/migrations/`、`docs/skill-catalog.md` のうち該当する正本文書を更新する。
3. ユーザー影響がある場合は `CHANGELOG.md` に migration note を残す。
4. この索引には、新しい source of truth へのリンクまたは不変条件だけを足す。
