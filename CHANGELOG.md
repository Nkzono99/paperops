# 変更履歴

## Unreleased

- README、下流 README、AGENTS / CLAUDE、主要 docs を短縮し、重複していた運用説明や長いスキル解説を必要最低限の入口・境界ルール中心に整理した。
- main-text figure label が本文から参照されているかを確認する `figure-reference-check` を追加し、`make smoke` と下流 `make ci` に組み込んだ。あわせて method novelty の direct comparator、completion と equilibrium の混同、saturated heatmap / hidden threshold、claim-to-figure crosswalk と現行 figure role の drift を scientific / figure gate の checklist に追加した。
- 外部 export bundle を論文側へ取り込む前の `refs/imports/` import state と `external-import-check` を追加した。source index、integrity manifest、source commit / dirty state、artifact category、claim evidence policy、`must_not_claim` を warning 中心に確認し、partial / dirty candidate を supported evidence と誤読しにくくした。
- 既存下流でこの import gate を使う場合は、`pops update-paperops --apply` で管理対象の `Makefile`、`scripts/`、skill を更新し、必要に応じて `refs/imports/README.md` と `refs/imports/import-state-template.toml` を手動追加する。
- 外部 bundle import gate の説明を `refs/imports/README.md` へ寄せ、README / docs / AGENTS / CLAUDE 側は短い入口だけにした。
- `pops doctor` に残っていた旧 link schema 用の未使用 helper と、links invalid-kind の重複テストを削除した。
- 配布手順 docs から運用ルールの重複説明を外し、方針は `docs/change-policy.md` に寄せた。

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
