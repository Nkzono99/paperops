# 変更履歴

## Unreleased

- paper draft から runops project や一般ディレクトリを参照するための `refs/links.toml` link 台帳、`pops links list/check`、`make links-check`、追加解析・図表・実験要望ノートを追加した（#32）。既存下流リポジトリで取り込む場合は、必要に応じて `refs/links.toml` と `notes/research-requests.md` を手動追加し、個人環境の絶対パスは引き続き ignored な `refs/local/locations.toml` にだけ記録する。
- `notes/research-requests.md` に runops `research/paper_requests.toml` への handoff 手順と TOML 例を追加し、paper 側の request status を runops contract と揃えた。runops 側の `runops.paper.request.draft` に対応し、duplicate id のまま転記しない注意を加えた（runops#75, runops#77）。
- HarnessOps 0.1.10 の repo-local skill / bridge 更新を取り込み、`AGENTS.md` に `doctor` と `update-harness` の短い運用導線を追加した。
- GitHub Flow を採用し、`main` への直接 push を禁止する運用へ移行した。PR では `Smoke / smoke` を必須チェックとして通し、release tag と GitHub Release は `main` に merge 済みの commit にだけ作成する。PyPI publish workflow も release tag が `origin/main` から到達可能な場合だけ公開するようにした。

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

## 0.3.0 - 2026-04-14

- `tex-env.example.toml` と `scripts/tex-env.sh` を追加: ユーザー空間 TeX Live や Docker ビルドに対応するための TeX 環境抽象化層（#6）
- ビルドスクリプト（`build-ja.sh`、`build-en.sh`）を `tex-env.sh` に統合し、Docker モードと改善されたフォールバックメッセージを追加（#6）
- `frontmatter/` プレースホルダーに投稿先クラスで不要な場合の案内コメントを追加（#6）
- `journal.cls` がスターター用であることを明記するコメントを追加（#6）
- `/setup` スキルを追加: 初回プロジェクトセットアップ（venv 作成、設定ファイル生成、ワークフロー設定、メタデータ記入）を一括実行（#6）

## 0.2.0 - 2026-04-14

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
