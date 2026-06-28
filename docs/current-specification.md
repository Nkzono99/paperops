# paperops current specification index

この文書は現行仕様の正本ではなく、正本文書への索引である。古い「現行仕様書」は `architecture.md`、`cli.md`、migration docs、各 skill との重複が大きくなり、Agent が stale な説明を正本として読んでしまうリスクがあったため、ここでは入口と不変条件だけを管理する。

詳細がこの文書と食い違う場合は、下表の source of truth を優先する。

## Source Of Truth

| scope | source of truth | note |
| --- | --- | --- |
| architecture / layer contract | `docs/architecture.md` | root 層、下流論文層、`_paperops/`、`paper_ir`、workflow state、submission axis |
| CLI and checker behavior | `docs/cli.md`, `src/paperops/cli/`, `template/scripts/` | `pops init`、`pops update-paperops`、`pops scratch`、`pops workflow`、Makefile checks |
| migrations | `docs/migrations/` | 下流互換、legacy path、overlay migration |
| release and distribution | `docs/distribution.md`, `CHANGELOG.md`, `.agents/skills/release/SKILL.md` | package / tag / PyPI / scaffold version |
| skill routing | `docs/skill-catalog.md`, `template/.agents/skills/*/SKILL.md` | `.agents/skills/` が共通手順の source of truth |
| Claude Code wrappers | `template/.claude/skills/*/SKILL.md`, `template/scripts/check-skill-mirror.py` | wrapper は `.agents` source を import する互換入口 |
| downstream user interface | `template/README.md`, `template/AGENTS.md`, `template/CLAUDE.md` | 下流 project に配布される操作入口 |
| bibliography roots | `docs/cli.md`, `template/scripts/lint-bib.py`, `template/scripts/check-citations.py` | 標準 `.bib` は `manuscript/shared/bib/`、外部/import は `_paperops/refs/bib/curated/` と `_paperops/refs/bib/imported/`、legacy `refs/bib/` は互換読み取り対象 |

## Current Invariants

- root repository はテンプレート管理層であり、`template/` は下流論文 project に配布される scaffold である。
- 下流作成は `pops init` を正道とする。下流の project-owned extension は `AGENTS.project.md`、`CLAUDE.project.md`、`Makefile.project` に置く。
- 人間が普段触る入口は `story/`、`manuscript/`、`submission/`、review comments である。AI / harness が使う internal state は `_paperops/` に置く。
- 旧 top-level `notes/`、`refs/`、`claims/`、`evidence/`、`contracts/`、`workflow/` などは互換読み取り対象に留める。
- `paper_ir` と section plan は生成一時物であり、必要な場合だけ `.paperops/cache/` に置く。
- `manuscript/` は living manuscript / authoring source であり、投稿後や査読後も編集してよい。
- `submission/` は submission candidate、round snapshot、submitted / under-review / revision-candidate の証跡を置く派生層である。
- `submission-gate` は authoring source から submission candidate へ切る前の strict gate であり、`check-predicted-results.py`、authoring intent、open AREQ、submission drift を確認する。
- 原稿完成 route、予測稿、図設計、block flow、section compiler の詳細は `docs/skill-catalog.md` と各 `template/.agents/skills/*/SKILL.md` を正本にする。

## Update Rule

この索引へ詳細仕様を追加しない。新しい挙動を導入する場合は、次の順で更新する。

1. 実体の script / CLI / skill / template file を更新する。
2. `docs/architecture.md`、`docs/cli.md`、`docs/migrations/`、`docs/skill-catalog.md` のうち該当する正本文書を更新する。
3. ユーザー影響がある場合は `CHANGELOG.md` に migration note を残す。
4. この索引には、新しい source of truth へのリンクまたは不変条件だけを足す。
