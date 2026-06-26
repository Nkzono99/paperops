# 変更履歴

## Unreleased

- `section-depth-check` と `manuscript/writing-profile.yml` の `section_depth` floor を追加し、Results / Discussion が短すぎる場合に manuscript content blocker として検出できるようにした。JA 原稿は TeX noise を除いた `ja_chars`、EN 原稿は TeX noise を除いた `en_words` で数え、長さは target ではなく floor として扱う。既存下流リポジトリで取り込む場合は、`scripts/check-section-depth.py`、Makefile の `section-depth-check` / `finish-manuscript-check` / `pre-submit` 接続、`manuscript/writing-profile.yml` の `section_depth`、Results / Discussion contract、AGENTS / CLAUDE / README、`finish-manuscript` / `review-public-manuscript` を更新する必要がある。
- `AGENTS.project.md`、`CLAUDE.project.md`、`Makefile.project` を下流 scaffold に追加し、project 固有の恒久指示と tracked Make target を paperops-managed core から分離した。`Makefile.local` は ignored な個人環境用拡張として扱い、`.agents/skills/project-*` と `.claude/skills/project-*` は `update-paperops` の managed update 判定から除外する。
- 下流 scaffold の AI/ハーネス内部状態を `_paperops/` に集約し、人間向けの高次構想層として `story/` と `story/story-seed.md` を追加した。`contracts/`、`workflow/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` は `_paperops/` 配下へ移動し、scripts / CLI は modern path を優先しつつ旧 top-level path も互換読み取りする。既存下流リポジトリで取り込む場合は、管理対象の `AGENTS.md`、`CLAUDE.md`、`README.md`、`Makefile`、`scripts/`、skill、`_paperops/defaults/` を更新し、プロジェクト固有のカード・refs・notes は手動で移行する。
- `_paperops/defaults/contracts/` と `_paperops/defaults/workflow/` を追加し、paperops-managed の標準 contract / workflow kernel を project overlay から分離した。`_paperops/contracts/` は contract overlay、`_paperops/workflow/` は current-state / decisions / round-summary と任意の workflow overlay を置く場所になる。`pops update-paperops` は defaults を managed update 対象にし、`pops migrate show/apply M0-0002` は既存 overlay を自動削除しない no-move migration item として defaults 分離手順を示す。既存下流リポジトリで取り込む場合は `pops update-paperops --apply` で `_paperops/defaults/` を追加し、既存 `_paperops/contracts/*.yml` や `_paperops/workflow/machine.yml` は review 済みになるまで overlay として残す。
- `pops migrate list/show/apply` と migration item `M0-0001` を追加し、旧 top-level の `contracts/`、`workflow/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` を `_paperops/` 配下へ移す定型 migration を提供した。今後は checkpoint release ごとに migration handler を持ち、最新 `pops` に古い互換 fallback を無期限に残さない。
- workflow を C 案へ更新し、`SCOPED -> STORY_SEEDED -> EVIDENCE_PLANNED -> EVIDENCE_READY -> STORY_RECONCILED -> ARCHITECTURE_LOCKED -> SECTION_PLANNED` の story-first 状態列を追加した。原稿前の素朴な story seed、evidence plan、実結果との reconciliation、section architecture lock を分け、`finish-manuscript` や content-first checks が新 state / guard を見るようにした。
- `docs/architecture.md` と `docs/current-specification.md` を新レイアウト前提で書き直し、`story/`、`_paperops/`、`paper_ir`、section compiler、subagent roster、Mermaid workflow、移行方針を明文化した。

## 0.9.0 - 2026-06-25

- `pops scratch restart` を追加し、`archive` だけでは現行 `manuscript/`、`submission/`、`notes/`、`refs/`、`evidence/`、`claims/`、`review/`、`requests/` が残る問題を避け、sealed archive 作成後に同じ repo を starter 状態へ戻せるようにした。`--include-handoff` 指定時は `_handoff/` payload も封印してから reset する。既存下流リポジトリで取り込む場合は、CLI 更新に加えて `/archive-scratch`、README、AGENTS / CLAUDE の archive 手順を更新する必要がある。
- direct-engine fallback の BibTeX 実行時に `BIBINPUTS` / `BSTINPUTS` を絶対パスで設定し、`build/` ディレクトリから `bibtex main` を実行しても共有 `.bib`、`.bst`、投稿先 slot の style を解決できるようにした。既存下流リポジトリで取り込む場合は、`scripts/build-ja.sh`、`scripts/build-en.sh`、`scripts/build-submission.sh` を更新する必要がある。closes #69
- 投稿前 `readiness-check --require-submission` を強化し、author ORCID / email / corresponding author、code/data license、Open Research DOI または persistent URL、data/software citation key の `.bib` 接続、human verification、投稿版 front matter / Key Points / Abstract / Open Research Statement の未確定値を error として検出するようにした。既存下流リポジトリで取り込む場合は、`manuscript/publication-metadata.toml` と `scripts/readiness-check.py` を更新し、投稿前に `[submission]`、`[open_research]`、`[human_verification]` を埋める必要がある。closes #70

## 0.8.0 - 2026-06-25

- `/archive-scratch` skill を追加し、`pops scratch archive/list/inspect/reset/restore` を使った過去稿封印、1からの書き直し、明示時だけの復元確認を下流テンプレートの標準入口にした。既存下流リポジトリで取り込む場合は、新 skill、Claude wrapper、AGENTS / CLAUDE / README の skill 入口を追加する必要がある。
- `scripts/build-submission.sh`、`audit-build-log.py`、`PAPEROPS_RUNNER_PREFIX` を追加し、`submission/<venue>/main.tex` の opt-in PDF build、build log audit、HPC / CI runner prefix をテンプレート標準にした。既存下流リポジトリで取り込む場合は、新 script、Makefile の `build-submission` target、`tex-env.example.toml`、`submission/README.md` を更新する必要がある。closes #68
- `workflow/subagent-roster.yml` と review round の Subagent delegation ledger を追加し、`finish-manuscript` が main agent / orchestrator として story_architect、evidence_auditor、results_structure_reviewer、discussion_function_reviewer、public_reader、submission_hygienist などの subagent report を feedback card、claim/evidence update、section plan へ統合する導線を明文化した。既存下流リポジトリで取り込む場合は、新 roster、review card templates、peer-review view、AGENTS / CLAUDE / README、`finish-manuscript` を更新し、review round に integration decision 欄を追加する必要がある。
- `focus-policy.yml`、`check-content-first.py`、`content-first-check`、`finish-manuscript-check` を追加し、原稿完成 goal 中に Results hierarchy / Discussion functions / claim scope などの本文 blocker が残ったまま Submission hygiene や downstream harness 改修だけへ逸れる作業を検出できるようにした。`pops workflow route-review --issue-class submission-loop --apply` は STRUCTURE_ACCEPTED 系 guard が未達なら拒否する。既存下流リポジトリで取り込む場合は、新 script、Makefile target、`workflow/focus-policy.yml`、`workflow/current-state.yml` の `CONTENT_FIRST` guard、`workflow/machine.yml` の guard、`finish-manuscript` / `design-paper-storyline` / `integrate-writing-feedback`、review card templates、AGENTS / CLAUDE / README を更新する必要がある。
- `design-paper-storyline`、`contracts/storyline.yml`、`notes/views/storyline.md`、`check-storyline.py` を追加した。個別 section より上位で reader_promise、evidence_ladder、Results hierarchy、Discussion functions を固定し、原稿内容が未解決のまま Submission hygiene や readiness-check 改修へ進む失敗を防ぐ。`finish-manuscript`、`audit-ai-draft`、`peer-review-manuscript`、`review-public-manuscript` は content-first / editorial architect 方針へ更新した。既存下流リポジトリで取り込む場合は、新 skill、new contract、new view、`scripts/check-storyline.py`、Makefile target、`workflow/` guard を手動で追加する必要がある。
- `check-quantity-integrity.py` と result card の `quantity_contracts` を追加した。本文に出る `N of D` 型の数量を `value`、`denominator`、`unit_of_analysis`、`aggregation`、`source_artifact` へ接続し、同じ比率でも解析単位が変わる事故を検出できるようにした。既存下流リポジトリで取り込む場合は、`scripts/check-quantity-integrity.py`、Makefile target、必要な result card の `quantity_contracts` を追加する。
- `plan-figure-story`、`contracts/figures.yml`、`figure-obligation-check` を追加した。中心 claim から本文生成前に visual obligation を作り、state/setup 図、criterion 図、primary evidence 図、mechanism/boundary 図の missing figure を検出できるようにした。既存下流リポジトリで取り込む場合は、新 skill、new contract、`scripts/check-figure-obligations.py`、Makefile target、`workflow/` guard、`manuscript/writing-profile.yml` の figure requirements、claim / figure card template の crosswalk field を手動で追加する必要がある。
- 下流 GitHub Actions の reusable workflow 参照を `YOUR_ORG/paperops` placeholder から `Nkzono99/paperops` に変更し、`pops init` 直後の初回 setup warning を減らした。fork や自前 upstream を使う場合だけ workflow `uses:` を手動で差し替える。
- `notes/views/*.md` に `view_type` と `source_of_truth` の front matter を追加し、pure overview view と controlled authoring view の違いを機械可読にした。`paper-layer-card-check` でも view metadata を検査する。
- `/resolve-local-paths` を runops ディレクトリリンクの入口として明確化し、`runops-main`、`pops links list --resolve-local`、paper request handoff の確認手順を追記した。

## 0.7.0 - 2026-06-25

- `workflow/` と `pops workflow` を追加し、論文執筆プロセスを固定の階層型状態機械と section 依存グラフとして扱えるようにした。全体状態、section 状態、Issue Router、transition guard、loop policy、stale 伝播を `workflow/machine.yml` と `workflow/current-state.yml` に持たせ、`workflow-check` と `finish-manuscript` に接続した。
- `contracts/` と `manuscript/writing-profile.yml` を scaffold に追加した。章ごとの文章テンプレートではなく、Introduction / Methods / Results / Discussion / Conclusion の読者質問、入力、出力、禁止構造を定める入出力契約として扱い、論文種別・投稿先 overlay を重ねてから `plan-section -> draft-section -> audit-section` へ進める。生成した section plan は `.paperops/cache/` に置き、Git 管理しない。
- `paper_ir` と section compiler の仕様を追加した。card 正本と controlled authoring view から Writer 用 context を生成一時物として作り、Results / Discussion / Methods の読者向け構造へ変換してから本文を書く方針を docs、downstream AGENTS / CLAUDE、`finish-manuscript` に反映した。あわせて `make ci` を構造確認、`make audit` を advisory authoring checks、`make pre-submit` を投稿前 profile として分離し、template Makefile の Python fallback を Windows-safe にした。
- `latexmk` がない環境でも `PAPER_TEMPLATE_RUN_LATEX=1` 時に direct-engine fallback を試すようにした。JA は `xelatex`、EN は `lualatex` を優先し、`bibtex` と追加 LaTeX pass を走らせ、PDF 未生成や `Missing character` を明確に失敗として扱う。
- 公開原稿と notes の読みやすさ guard を強化した。`target-snapshot sample`、`exposure diagnostic`、`not evidence` などの内部 analysis label / defensive wording を starter terminology で検出し、`notes/**/*.md` の label-only 行には前提・判断根拠・本文への影響を書くよう `argument-focus-check` が警告する。
- 論文 claim gate と査読ループのカードを拡張した。central assumption ledger、claim stress-test、external validation gate、path criterion、evidence-design coverage、figure state visualization、response closure audit を scaffold と skill に追加し、AI が補助 artifact や応急的な原稿修正を claim support / review closure と誤読しにくくした。
- Skill context budget warning の導線を追加した。`TROUBLESHOOTING.md` と `pops doctor` で、warning は skill 本体が読めない通知ではなく description 圧縮であること、通常執筆・GitHub・解析時の plugin profile 目安を示す。
- `pops scratch archive/reset/restore/list/inspect` を追加し、同じ論文 repo 内で現行の `manuscript/`、`notes/`、`refs/`、カード層などを `_archives/` の split bundle に封印してから1から書き直せるようにした。archive part は既定で 48 MiB に分割し、通常の AI 執筆では `_archives/` を読まないルールと `archive-seal-check` を追加した。
- `research-request-handoff-check` を追加し、paper 側の open analysis request と linked runops project の `paper_request_queue` の drift を warning できるようにした。`runops_id = draft:*`、queue 未登録、local path 未解決、status mismatch を検出し、`pre-submit` では strict に確認する。
- repo-local の HOPS 関連 skill vendor copy を削除し、HarnessOps plugin から参照する方針へ寄せた。
- `concept-term-check` と `notes/views/concept-terms.md` を追加した。AI 初稿で起きやすい hyphen / slash compound や強い英語名詞句への単語化を、claim / argument / evidence card の意味を本文語彙へ圧縮する問題として扱い、頻度、表記揺れ、一文内の詰め込み、accepted / plain-language / avoid の判断を確認できるようにした。

## 0.6.0 - 2026-06-24

- README、下流 README、AGENTS / CLAUDE、主要 docs を短縮し、重複していた運用説明や長いスキル解説を必要最低限の入口・境界ルール中心に整理した。
- main-text figure label が本文から参照されているかを確認する `figure-reference-check` を追加し、`make smoke` と下流 `make ci` に組み込んだ。あわせて method novelty の direct comparator、completion と equilibrium の混同、saturated heatmap / hidden threshold、claim-to-figure crosswalk と現行 figure role の drift を scientific / figure gate の checklist に追加した。
- 外部 export bundle を論文側へ取り込む前の `refs/imports/` import state と `external-import-check` を追加した。source index、integrity manifest、source commit / dirty state、artifact category、claim evidence policy、`must_not_claim` を warning 中心に確認し、partial / dirty candidate を supported evidence と誤読しにくくした。
- 既存下流でこの import gate を使う場合は、`pops update-paperops --apply` で管理対象の `Makefile`、`scripts/`、skill を更新し、必要に応じて `refs/imports/README.md` と `refs/imports/import-state-template.toml` を手動追加する。
- 外部 bundle import gate の説明を `refs/imports/README.md` へ寄せ、README / docs / AGENTS / CLAUDE 側は短い入口だけにした。
- `pops doctor` に残っていた旧 link schema 用の未使用 helper と、links invalid-kind の重複テストを削除した。
- 配布手順 docs から運用ルールの重複説明を外し、方針は `docs/change-policy.md` に寄せた。
- `/goal` で原稿を完成まで進める `finish-manuscript` skill を追加した。1からの執筆、既存稿の改稿、peer review / editor feedback loop、上流 card への遡及を扱う。
- `setup` と `resume-session` skill を軽量な入口へ整理し、常時読む項目と必要時に読む意味論ビューを分けた。

## 0.5.0 - 2026-06-23

- 論文執筆の中間層をカード正本へ整理した。`evidence/`、`claims/`、`review/`、`requests/` を追加し、result / figure / source、claim / scientific gate / argument、feedback / response、analysis / writing request を小さな Markdown card + front matter で管理できるようにした。旧 `notes/*.md` は互換ビューへ降格し、俯瞰用の `notes/views/` を追加した。
- 人間の原稿レビューやプロンプト指示を本文だけの局所修正に閉じないため、`/integrate-writing-feedback` を追加した。指摘を `review/feedback/` の feedback card にし、`upstream_routes` に従って claim scope、scientific gate、evidence card、analysis / writing request、最後に manuscript block へ反映する導線を明文化した。
- `make paper-layer-card-check` を追加し、`evidence/`、`claims/`、`review/`、`requests/`、`notes/views/`、旧互換ビューの外形を検査するようにした。`make smoke` と下流 `make ci` にこの検査を組み込んだ。
- 既存下流リポジトリで取り込む場合は、管理対象の `AGENTS.md`、`CLAUDE.md`、`Makefile`、`scripts/`、`.agents/skills/`、`.claude/skills/` を更新したうえで、プロジェクト固有内容として `evidence/`、`claims/`、`review/`、`requests/`、`notes/views/` を手動追加する。既存の `notes/result-pattern-map.md`、`notes/claim-evidence-map.md`、`notes/scientific-gate.md` などは削除せず互換ビューとして残してよい。
- `pops init` の scaffold copy から `harness-feedback/`、`harness-lab/`、`.harness/`、`.harnessops/` を明示的に除外し、HarnessOps の local state が下流論文プロジェクトへ混入しないようにした。

## 0.4.0 - 2026-06-23

- 論文を書く前の中間層を拡張した。`/map-result-patterns` と `notes/result-pattern-map.md` で simulation results、figure data、analysis artifact を result pattern / evidence packet に束ね、`/scientific-gate` と `notes/scientific-gate.md` で中心主張、Abstract、Conclusion、主要図表の claim readiness、人間承認、再現性、仮定の blocker を確認できるようにした。
- AI 初稿をそのまま磨かず、論旨設計へ戻す導線を追加した。`/audit-ai-draft`、`/contextualize-conditions`、`/polish-ai-draft`、`notes/argument-map.md`、`notes/condition-context-map.md`、`notes/ai-draft-polish.md`、`make argument-focus-check` により、条件数列挙、防御的 caveat、内部 provenance 語、AI 文章の定型臭を分けて扱う。
- 関連研究、外部 source、査読導線を強化した。`/source-reach-scan`、`/research-related-work`、`/peer-review-manuscript`、`/respond-to-peer-review`、`notes/source-reach.md`、`notes/related-work-map.md`、`notes/peer-review.md`、`refs/research/`、`refs/source-reach/` を追加し、raw findings や confidential reviewer correspondence は Git 管理しない一時領域に留め、確認済みの要約・comment ID・revision route だけを tracked notes / refs へ昇格する。
- 執筆ハーネスを俯瞰する `/open-paper-scan` を追加し、改善指示が局所修正へ固着する前に、原稿・読者体験・skill design・評価不能性・管理過多を発散的に眺められるようにした。出た idea はその場で採用せず、必要になったものだけ後段の gate / research / writing skills へ渡す。
- `pops init` で `_handoff/` 受け取り箱を作成し、人間から AI へ渡す未整理ファイルを Git 管理しない一時領域へ置けるようにした。`refs/` と `notes/` の作業用ドキュメントは日本語で書く方針を明示し、スターターノートと参照テンプレートの見出しを日本語化した。
- 公開原稿ガードを強化した。公開原稿へ内部 provenance 語が混入しないよう starter terminology と writing skills を見直し、公開原稿の既定 bibliography は `references` のみにし、`mypapers` は作業 draft 用の opt-in 枠として readiness warning の対象にした。`mirror-freshness-check --strict` と `make mirror-strict-check` を追加し、`make pre-submit` で freshness warning を失敗扱いにするようにした。
- scaffold 配布の安全性を強化した。Git では ignore される `_handoff/` の未整理 payload、`refs/source-reach/**/raw/**`、source reach の generated doctor / capture artifact が wheel 内の bundled scaffold や wheel-installed `pops init` 出力へ混入しないよう、package boundary guard と CLI tests を更新した。
- PyPI 公開 workflow の安定性を修正した。Trusted Publishing workflow で `uv` を用意し、tag fetch 時の衝突を避けるようにした。
- 外部発想源として Academic Research Skills Codex、Deep-Research-skills、Humanizer-zh、Agent Reach、AI peer review 系ツールの型を参考にした。ただし CC BY-NC 4.0 の Academic Research Skills Codex 由来部分は文面やテンプレートをコピーせず、paperops-native な notes / refs / skill workflow として再設計した。
- 既存下流リポジトリで取り込む場合は、`pops update-paperops --apply` で管理対象 skill / script を更新したうえで、新規 notes / refs、`_handoff/README.md`、`_handoff/.gitkeep`、`.gitignore` の `_handoff/*` と `refs/source-reach/**/raw/**` などの ignore block を必要に応じて手動追加する。

## 0.3.0 - 2026-06-22

- release 前の version truth preflight として `scripts/check-release-version-truth.py` を追加し、release skill から `pyproject.toml` / `src/paperops/__init__.py` / `CHANGELOG.md` / tag / GitHub Release の不整合を検出できるようにした。旧 template 時代の履歴見出しは package release 見出しと区別できる archive 表記へ整理した。
- `paper-harness-cli` の release 前検証に scaffold package boundary guard を追加した。ignored/generated scaffold artifact は wheel 内の bundled scaffold と wheel-installed `pops init` の出力に混入しないことを `scripts/check-scaffold-package-boundary.py` と PyPI publish workflow で検査する。
- `pops update-paperops` の plan 表示に管理対象ファイルの更新面ラベルと changed file の扱いを追加した。既存下流リポジトリで取り込む場合、`changed managed files` は通常の `--apply` では上書きされず、差分確認後に必要なものだけ `--apply --force` する判断材料として使える。
- `pops doctor` の成功時に、検査範囲が構造とローカルセットアップであり、公開・投稿前品質は `make readiness-check` / `make pre-submit` で確認することを明示した。既存下流リポジトリ側のマイグレーションは不要。
- `AGENTS.md` / `CLAUDE.md` と skill catalog に、状況別の skill 入口を追加した。既存下流リポジトリで取り込む場合は、管理対象の `AGENTS.md`、`CLAUDE.md` の案内を更新するだけで、既存 skill 名やファイル配置のマイグレーションは不要。
- `readiness-check` が `notes/decision-log.md` の欠落を検出するようにした。既存下流リポジトリで取り込む場合、恒久的な判断の記録先として `notes/decision-log.md` を残すか、欠落している場合は作成する。
- project skill の source of truth を `.agents/skills/` 側へ移し、`.claude/skills/` は `@${CLAUDE_SKILL_DIR}/../../../.agents/skills/<skill>/SKILL.md` で共通手順を読む Claude Code wrapper にした。既存下流リポジトリで取り込む場合は、`.agents/skills/` と `.claude/skills/` を同時に更新し、ローカルで変更した skill がある場合は `.agents/skills/<skill>/SKILL.md` 側へ手動マージする。
- HarnessOps 0.1.16 の local storage 導線へ移行し、target 側の `harness-lab/` 正本を repo 外の `~/.harnessops/projects/paper-harness-template/` に置くようにした。repo には `.harnessops/project.toml` のリンク情報だけを残し、`harness-lab/`、`harness-feedback/`、`.harnessops/lock.json` は version 管理対象から外した。下流 project repo で HOPS を使う場合も、`uvx --from harnessops hops project link --profile paper-harness-project` で `harness-feedback/` を local state に展開する。
- 一人開発に合わせ、分岐運用と必須 gate を既定運用から外した。通常は `main` に直接取り込み、`make smoke` はリスクの高い変更や公開前確認で必要な場合に使う。
- paper draft から runops project や一般ディレクトリを参照するための `refs/links.toml` link 台帳、`pops links list/check`、`make links-check`、追加解析・図表・実験要望ノートを追加した（#32）。既存下流リポジトリで取り込む場合は、必要に応じて `refs/links.toml` と `notes/research-requests.md` を手動追加し、個人環境の絶対パスは引き続き ignored な `refs/local/locations.toml` にだけ記録する。
- `notes/research-requests.md` と `/resolve-local-paths` に runops `research/paper_requests.toml` への handoff 手順を追加し、paper 側の request status を runops contract と揃えた。runops 側の `runops.paper.request.draft` に対応し、duplicate id のまま転記しない注意を加えた（runops#75, runops#77）。
- README と architecture / distribution docs に runops link の情報境界、MCP 優先の確認導線、既存下流への取り込み方針を整理した。
- HarnessOps 0.1.11 の repo-local skill / bridge 更新を取り込み、open issue triage 導線を追加した。
- HarnessOps 0.1.10 の repo-local skill / bridge 更新を取り込み、`AGENTS.md` に `doctor` と `update-harness` の短い運用導線を追加した。

## 0.2.0 - 2026-05-14

- Python 実行環境の案内を Python 3.11 固定ではなく Python 3.11 以上の要件として明確化した。既存下流リポジトリで取り込む場合は `AGENTS.md`、`CLAUDE.md`、`README.md` の文言更新のみで、マイグレーション作業は不要。
- `pops` の標準実行経路を `uvx --from paper-harness-cli pops ...` に一本化した。`pops init` / `pops setup` は `.pops/manifest.toml` の作成・採用だけを行い、project-local `.venv` への `paper-harness-cli` インストールは行わない。`pops doctor` は `.venv/pops` 不在を警告せず、既存 `.venv` が壊れている場合と `uvx` / `uv` 不在だけを警告する。既存下流リポジトリの `.venv` は論文プロジェクト用 Python 環境として残してよいが、`pops` 実行には使わない。
- `pops update-paperops --plan` / `--apply-chain` を追加し、minor checkpoint ごとの exact `uvx --from paper-harness-cli==<version>` 呼び替えで scaffold を段階更新できるようにした。`.pops/manifest.toml` には `scaffold.layout_version` と `[upgrade]` を記録し、最新 `pops` に古い migration を無限保持しない方針を `docs/upgrade-policy.md` に明文化した。既存下流リポジトリで取り込む場合は、まず `uvx --from paper-harness-cli pops update-paperops --plan` で chain を確認する。
- `pops update-paperops` を管理対象ハーネス更新の主コマンドにし、旧 `pops update-harness` は互換 alias として残した。`pops` は TTY 上の通常実行時に PyPI の `paper-harness-cli` 最新版、実行中の `pops` version、`.pops/manifest.toml` に記録された適用済み scaffold version を比較し、更新がある場合は `uvx --from paper-harness-cli pops update-paperops --plan` と `/update-paperops` スキルでの chain 確認を案内する。既存下流リポジトリで取り込む場合は、新規 `update-paperops` skill、AGENTS/CLAUDE のスキル一覧、`docs/cli.md` の新コマンド名を反映する。
- 下流移行で見つかった scaffold 摩擦を修正した。`pops update-paperops` は既存 `.pops/manifest.toml` の未知 key と `template_ref` を保持し、`--template-ref` または Git worktree の `--source` から適用元 ref を記録できるようにした（#24）。scaffold 内の旧 `paper-harness-template` / `paper-harness-scaffold-template` 参照を `paperops` / `pops` 導線へ統一した（#23）。`check-tex-structure.py` は section file から main.tex の language root 基準の図パスと `manuscript/shared/style/**` の `.bst` を解決する（#25）。Makefile とビルドヘルパーの Python 選択を `.venv`、`python3.11`、`python3`、`python` の順に揃え、`tex-env.toml` / 環境変数で JA / EN ごとの `latexmk` mode、`latex`、`dvipdf` を設定できるようにした（#26, #27）。既存下流リポジトリで取り込む場合は、管理対象の `Makefile`、`scripts/`、`.claude/skills/`、`.agents/skills/`、`AGENTS.md`、`CLAUDE.md`、`README.md`、`tex-env.example.toml` を更新し、旧 `raise-template-feedback` や旧 source repo 参照が残る場合は削除する。
- CLI 主導の配布導線として Python パッケージ `paper-harness-cli` と `pops` entrypoint を追加し、GitHub リポジトリ名を `paperops` に変更した。PyPI の `paperops` / `paper-ops` 名は既存プロジェクトとの衝突または類似名ブロックに当たるため、distribution 名は `paper-harness-cli`、CLI 名は `pops` とする。`init`、`setup`、`doctor`、`update-paperops`（旧 `update-harness` 互換 alias）、`migrate`、`feedback`、`version` の最小サブコマンドを実装し、`pops init` は `template/` を bundled scaffold として展開して `.pops/manifest.toml` を作成する。あわせて旧 scaffold 公開 workflow / helper script を廃止し、PyPI Trusted Publishing workflow と root の `make smoke` 用 `cli-smoke` を追加した。既存下流リポジトリで CLI 管理へ寄せる場合は `uvx --from paper-harness-cli pops setup` を実行し、旧 scaffold 判定だけ確認したい場合は `uvx --from paper-harness-cli pops migrate --apply` を使う。`raise-template-feedback` は `feedback-paper-harness` に改名した。
- レビュー報告の残課題として、`.agents/skills` と `.claude/skills` の対応を検査する `scripts/check-skill-mirror.py`、TeX の `\input` / `\include` / `\includegraphics` / bibliography / style 参照を検証する `scripts/check-tex-structure.py`、biblatex 系 citation command 対応、`lint-bib --mode pre-submit` の引用サマリー検査、`readiness-check --require-submission` を追加した。あわせて `/review-public-manuscript` を section / weekly / pre-submit の public-only gate として明文化し、`tex-env.sh` の shell eval を廃止、`journal.cls` の投稿先 class 方針と `.gitignore` の raw PDF 保護を更新した。既存下流リポジトリで取り込む場合は新規 script、Makefile target、`.gitignore`、review skill、README/AGENTS/CLAUDE の案内を反映する必要がある。
- 残りロードマップの実装として、`/calibrate-claims`、`/public-terminology-pass`、`/paragraph-surgery`、`/figure-story-audit`、`/venue-fit-review`、`/ai-disclosure-check` を追加し、claim strength、公開語彙、段落流れ、figure story、投稿先 fit、AI 開示を工程別に点検できるようにした。あわせて `scripts/mirror-freshness-check.py` と `manuscript/mirror/block-ledger.yml`、`scripts/check-submission-drift.py` を追加し、`make ci` / `make pre-submit` / `make smoke` に接続した。既存下流リポジトリで取り込む場合は新規 skill、script、`block-ledger.yml`、Makefile target、AGENTS/CLAUDE/README の案内更新が必要。
- Sprint 2 の品質チェックとして、公開原稿に残る内部語・禁止語を検出する `scripts/check-public-terms.py` と、supported claim の evidence / scope / manuscript block 対応を確認する `scripts/check-claim-evidence.py` を追加し、`make ci` / `make smoke` に組み込んだ。PR テンプレートに論文品質チェックを追加し、refs summary template で文献サマリーの検証状態を記録できるようにした。あわせて Windows の `make` からも shell script target を実行できるよう、`build-ja` / `build-en` / `export-arxiv` は `bash scripts/...` 経由にした。既存下流リポジトリで取り込む場合は新規 script、Makefile target、PR テンプレート、`refs/summaries/summary-template.md`、`readiness-check.py` の placeholder 追加を反映する必要がある。
- Sprint 1 の即効改善として、`scripts/export-arxiv.sh` が generated figures 不在でも失敗しないようにし、`/pull-template-updates` の古い `docs/` パス参照と `/setup` の `refs/local/locations.toml` 自動作成案内を現行の安全運用へ更新した（#16, #17, #18）。既存下流リポジトリでは任意導入だが、取り込む場合は該当 script と skill の更新、README の setup 案内を反映する必要がある。
- 論文品質ゲートの土台として `notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`.claude/rules/writing-quality.md` を追加し、`manuscript/mirror/terminology.yml` を public terminology gate 形式に拡張した（#19, #20, #21）。既存下流リポジトリでは任意導入だが、取り込む場合は新規 notes/rule、`terminology.yml` schema、`readiness-check.py` の追加 placeholder チェック、AGENTS/CLAUDE/README の案内更新が必要。
- TeX 直編集レビューの導線として `/start-manuscript-review` と `/collect-manuscript-review` を追加し、`scripts/collect-manuscript-review.py` で `git diff` と `% REVIEW:` / `% AI:` / `% Q:` / `% KEEP?:` / `% TODO-PAPER:` を `notes/reviews/review-YYYY-MM-DD.md` に回収できるようにした（#15）。既存下流リポジトリでは任意導入だが、この運用を使う場合は新しい skill、script、`.claude/settings.json` の追加許可、AGENTS/CLAUDE/README の案内を取り込む必要がある。
- Manubot、Quarto journal templates、rrtools を一時クローンして参考にし、下流論文リポジトリ向けに `make readiness-check` / `make pre-submit`、`manuscript/publication-metadata.toml`、`notes/reproducibility.md`、原稿レビュー・エビデンス不足・ハーネス摩擦の Issue フォームを追加。既存下流リポジトリでは任意導入だが、共有・投稿前の運用に使う場合は新規ファイルをコピーし、`Makefile` と PR テンプレートを更新する必要がある。
- TeX 本文中の `\cite{...}` / `\citep{...}` 等が `.bib` に存在するかを確認する `scripts/check-citations.py` と `make citation-check` を追加し、`make ci` / `make smoke` に組み込んだ。既存下流リポジトリで取り込む場合は `scripts/check-citations.py` と `Makefile` の target 更新が必要。
- `latexmk -output-directory` 使用時に bibtex が共有 `.bib` を解決できない問題を修正。`BIBINPUTS` / `BSTINPUTS` を設定し、スターター原稿の `\bibliography{}` は `references,mypapers` のようなベース名指定に変更（#7）。既存下流リポジトリでは `\bibliography{../shared/bib/...}` の接頭辞を外す必要がある。
- Windows / PowerShell から PDF をビルドする `scripts/build-ja-pdf.ps1` と `scripts/build-en-pdf.ps1` を追加。pinned Tectonic を `.tools/` に取得し、`-NoDownload` でネットワーク取得を禁止できる（#9）。
- Codex 用に `template/.agents/skills/` を追加し、既存 `.claude/skills/` を source of truth とする同名 skill の互換入口を提供（#12）。
- 投稿先公式テンプレートと最終提出用 TeX を `submission/<venue>/` に分離する標準スロットを追加し、build output と投稿用ローカルツールを ignore（#10）。
- 投稿前原稿を外部読者視点でレビューする `/review-public-manuscript` skill を追加。公開原稿だけを入力に、未定義語、再現性ギャップ、追加解析候補、対応チェックリストを抽出する（#8）。
- nested private paper repo 運用と Windows の dubious ownership / `safe.directory` 対応を `TROUBLESHOOTING.md`、AGENTS/CLAUDE、template 更新 skill に追記（#11）。
- 作業報告型の原稿を主張中心の論文構造へ再設計する `/design-manuscript-claims` skill を追加。主張、証拠、補助解析、対照、限界を分け、必要時のみ block ID 単位の rewrite plan に進む（#13）。
- `/review-public-manuscript` に一般研究者視点の `reader-assumptions` / `local-terminology` / `public-reproducibility` チェックを追加。公開原稿だけでローカル語、実装語、図表ラベル、件数内訳、Data availability の暗黙前提を検出できるようにした（#14）。

## Template archive 0.3.0 - 2026-04-14

- `tex-env.example.toml` と `scripts/tex-env.sh` を追加: ユーザー空間 TeX Live や Docker ビルドに対応するための TeX 環境抽象化層（#6）
- ビルドスクリプト（`build-ja.sh`、`build-en.sh`）を `tex-env.sh` に統合し、Docker モードと改善されたフォールバックメッセージを追加（#6）
- `frontmatter/` プレースホルダーに投稿先クラスで不要な場合の案内コメントを追加（#6）
- `journal.cls` がスターター用であることを明記するコメントを追加（#6）
- `/setup` スキルを追加: 初回プロジェクトセットアップ（venv 作成、設定ファイル生成、ワークフロー設定、メタデータ記入）を一括実行（#6）

## Template archive 0.2.0 - 2026-04-14

- 全ドキュメント・スキル・ルール・スクリプトのユーザー向けテキストを日本語化
- protect-files フックを廃止し、settings.json の deny パターン + rules/ による保護に移行
- validate-mirror フックを廃止（`make mirror-check` で手動実行に変更）
- SessionStart フックを廃止（`/resume-session` スキルに統合）
- `pull-template-updates` スキルを追加（上流テンプレート変更の下流取り込み）
- AGENTS.md を CLAUDE.md と同一内容に統一
- `git add` / `git commit` を permissions.allow に追加
- bib ファイルからダミーエントリを除去（コメントのみに）
- `/import-manuscript` スキルを追加（既存原稿のインポート支援）
- `docs/` を情報フローに沿って再配置: project-brief, contribution-claims → `notes/`、target-venue → `manuscript/venue.md`、writing-policy → `.claude/rules/`
- README のみのプレースホルダディレクトリ 17 個を削除、refs/ 構造をフラット化
- 用語管理を `manuscript/mirror/terminology.yml` に統一（`docs/terminology-ja-en.md` を廃止）
- `notes/session-context.md` と `notes/writing-log.md` を廃止（generated 版と handoff.md で代替）

## 0.1.0 - 2026-04-13

- `paper-template` リポジトリ構造を初期化
- ビルド、ミラー検証、リリースパッケージング用の再利用可能 GitHub ワークフローを追加
- Issue フォームとテンプレート保守スキルを追加
- `template/` 配下に下流論文スキャフォールド一式を追加
