# CLAUDE.md

ユーザーとは**日本語**でコミュニケーションすること。

これは**日英バイリンガル論文執筆ハーネス**である。日本語と英語の原稿はブロックレベルのミラーとして追跡される。

## セッションプロトコル

### 開始時

1. `/resume-session` を実行する。
2. 初回セッションの場合は `notes/project-brief.md` を読む。
3. 原稿テキストを編集する前に `manuscript/mirror/status.md` を確認する。

### 終了時

1. `/note-writing-session` を実行する。
2. 原稿構造や参考文献が変更された場合は `make ci` を実行する。

### コンパクション時

セッションコンテキストは PreCompact フックにより自動的に再注入される。コンパクション後、タスクの継続性が必要な場合は `notes/handoff.md` と `notes/todo.md` を再読する。

## 主要コマンド

```sh
uvx --from paper-harness-cli pops setup  # .pops を準備
uvx --from paper-harness-cli pops doctor # ハーネス状態を診断
uvx --from paper-harness-cli pops update-paperops --plan # 更新 chain を確認
make venv           # Python 3.11 以上で .venv を作成
make build-ja       # 日本語原稿をコンパイル（または構造検証）
make build-en       # 英語原稿をコンパイル（または構造検証）
make lint-bib       # 参考文献エントリを検証
make lint-bib-pre-submit # 引用済み key に refs/summaries の検証サマリーがあるか検証
make citation-check # TeX の citation key が .bib に存在するか検証
make mirror-check   # ja/ と en/ のブロックレベルのドリフトを検出
make mirror-freshness-check # 前回同期 ledger から ja/en block の更新を検出
make mirror-strict-check # mirror freshness warning を失敗扱いで検出
make public-terms-check # 公開原稿に内部語・禁止語が残っていないか検証
make argument-focus-check # AI 初稿の列挙・防御過多・ローカル条件依存を検出
make claim-evidence-check # supported claim に証拠と本文対応があるか検証
make paper-layer-card-check # evidence/claims/review/requests のカード層と互換ビューを検証
make submission-drift-check # submission/<venue> と manuscript/en の同期注意点を検出
make skill-mirror-check # .agents source と .claude wrapper の対応を検証
make links-check    # refs/links.toml と refs/local の link 対応を検証
make ci             # lint-bib + citation-check + mirror-check + mirror-freshness-check + public-terms-check + claim-evidence-check + paper-layer-card-check + skill-mirror-check + links-check + build-ja + build-en
make readiness-check # 公開メタデータ、再現性メモ、workflow 参照の未記入を検出
make pre-submit     # ci + lint-bib-pre-submit + submission 必須 readiness + submission-drift-check
make export-arxiv   # 英語原稿を arXiv 投稿用にバンドル
```

Windows / PowerShell では、PDF 確認用に pinned Tectonic を `.tools/` へ取得する wrapper を使える:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-ja-pdf.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-en-pdf.ps1
```

ネットワーク取得を禁止する場合は `-NoDownload` を付ける。

## ルール

- `manuscript/mirror/status.md` に別段の記載がない限り、`manuscript/ja/` が科学的なソースオブトゥルースである。
- `% block: ...` 識別子を保持する。削除や番号の振り直しは行わない。
- 保護されたファイルを直接編集しない: `manuscript/shared/figures/generated/**`、`refs/local/locations.toml`、`manuscript/shared/style/journal.cls`（settings.json の deny パターンが強制する）。
- `refs/` は**知識層**である。生の PDF よりキュレーション済みのサマリーを優先する。raw PDF は既定で ignore される `refs/papers/` に留め、引用キーは安定させる。
- 関連研究を広く集める場合は `/research-related-work` を使い、調査設計は `refs/research/`、議論は `notes/related-work-map.md`、採用文献は `refs/summaries/` と `.bib` へ分ける。raw search result や未検証 report を文献レビュー本文へ直接入れない。
- Web、GitHub、動画、RSS、SNS、議論サイトなど外部 source channel を使う場合は `/source-reach-scan` を使い、到達経路、credential need、raw capture policy、refs への昇格先を `notes/source-reach.md` と `refs/source-reach/` で分ける。
- `refs/links.toml` は外部 project / directory への共有 link 台帳である。tracked ファイルには絶対パスを書かず、`location_ref` を `refs/local/locations.toml` の個人設定で解決する。
- `refs/` と `notes/` に作る作業用ドキュメントは日本語で書く。citation key、field name、投稿先指定、外部ツール名などの識別子だけは英語のままでよい。
- `_handoff/` は人間から AI へ渡す未整理ファイルの一時受け取り箱である。内容は Git 管理されない。残す情報は `refs/` や `notes/` の適切な台帳へ整理し、秘密情報や個人環境の絶対パスを tracked ファイルへ移さない。
- `evidence/`、`claims/`、`review/`、`requests/` はカード正本である。`notes/views/` は人間が俯瞰するビュー、旧 `notes/*.md` は互換ビューとして扱う。
- 人間の原稿レビューやプロンプト指示は `/integrate-writing-feedback` で feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
- 俯瞰的な違和感や改善案を広げるだけなら `/open-paper-scan` を使い、ユーザーが求めるまで本文編集、notes 記録、Issue 化、上流 feedback 化へ進まない。
- simulation results、figure data、analysis artifact を本文に入れる前に、必要なら `/map-result-patterns` で `evidence/results/` と `evidence/figures/` のカードに result pattern / evidence packet として束ねる。
- 中心主張、Abstract、Conclusion、main figure caption を書く前に、必要なら `/scientific-gate` で `claims/gates/` の gate card と `notes/views/scientific-gate.md` の claim readiness を確認する。`analysis-needed` や `assumption-blocked` の主張を文体だけで本文に通さない。
- AI 初稿が条件数の列挙、run inventory、防御的 caveat に寄ったら、本文を直接磨く前に `/map-result-patterns`、`/audit-ai-draft`、`/contextualize-conditions` で `evidence/`、`claims/`、`notes/views/` を更新する。
- AI 初稿の機械的な文体だけを直す場合は `/polish-ai-draft` を使う。ただし、claim lock と AI 利用開示を守り、AI 検出回避を目的にしない。
- 投稿先公式テンプレートや最終提出用 TeX は `submission/<venue>/` に置き、`manuscript/ja,en` のミラー原稿と混ぜない。
- 公開・投稿前には `manuscript/publication-metadata.toml`、`notes/reproducibility.md`、`notes/ai-use.md` を更新し、`make pre-submit` を実行する。
- 新しい主張は `claims/claims/` の claim card に evidence、scope、limitation とともに記録し、`notes/views/claim-evidence-map.md` を俯瞰用に更新する。
- 想定読者や投稿先制約が変わったら `notes/reviewer-model.md` と `manuscript/venue.md` を更新する。
- 投稿前に査読者として厳しく読む場合は `/peer-review-manuscript` を使い、実際の査読コメントへ返答する場合は `/respond-to-peer-review` を使う。raw の editor / reviewer correspondence は confidential な場合があるため、tracked な `review/` カードには要約と comment ID を中心に残す。
- 内部 run label、script name、directory name、artifact name を本文の公開語として使わず、必要な置換を `manuscript/mirror/terminology.yml` に記録する。
- 1 節を書いた直後や週次の節目では `/review-public-manuscript` を `section` / `weekly` として使い、repo 内部文脈なしで公開語彙・暗黙前提・figure story を確認する。
- ミラー同期には `/sync-ja-en` を使用する。両言語を盲目的に上書きしない。
- JA/EN の確認済み同期後は `python scripts/mirror-freshness-check.py --root manuscript --update` で ledger を更新する。投稿前は `make mirror-strict-check` または `make pre-submit` で warning を残さない。
- 各セッションの終了時に `notes/handoff.md` と `notes/todo.md` を更新する。
- 恒久的な決定は `notes/decision-log.md` に記録する。

ファイル固有のルールは `.claude/rules/` にあり、対応するパスの編集時に自動的にロードされる。

## Git コミットルール

- git 操作前に `git rev-parse --show-toplevel` と `git remote -v` で対象 repo を確認する。nested private repo 運用では、親 repo と paper repo の変更を同じ commit に混ぜない。
- Windows の dubious ownership では、まず `git -c safe.directory=<repo> -C <repo> ...` の per-command 回避を使う。グローバル `safe.directory` 変更はユーザー判断にする。
- 意味のある作業単位ごとにコミットする。大量の変更を一つのコミットにまとめない。
- コミットメッセージは日本語で、変更の「なぜ」を記述する。
- `git push` は共有状態に影響するため、ユーザーの明示的な指示なしに実行しない。
- `git reset --hard`、`git push --force` 等の破壊的操作は、ユーザーが明示的に求めた場合のみ実行する。

## TeX 環境

ユーザー空間 TeX Live、Docker、または JA / EN ごとの LaTeX engine を使用する場合、`tex-env.example.toml` を `tex-env.toml` にコピーして環境を設定する。`tex-env.toml` がなければ従来通り PATH から `latexmk` を探し、既定の `latexmk -pdf` でビルドする。日本語ドラフトで `uplatex + dvipdfmx` が必要な場合は `[latex.ja]` の `latexmk_mode = "pdfdvi"`、`latex`、`dvipdf` を設定する。

## トラブルシューティング

- コンテキストが長くなったら `/compact` を実行する（目安: 50% 超過時）。
- `make ci` が失敗したら、まず `make lint-bib` と `make mirror-check` を個別に実行して原因を特定する。
- ミラーのドリフトが大量にある場合、`/sync-ja-en` で一括同期せず、セクション単位で対処する。
- 設定の優先順: `.claude/settings.local.json`（個人） > `.claude/settings.json`（プロジェクト） > `~/.claude/settings.json`（グローバル）。
- nested repo や `safe.directory` で迷ったら `TROUBLESHOOTING.md` を確認する。

## 利用可能なスキル

Claude Code では `.claude/skills/` の同名 skill を入口として使う。恒久的な手順変更は `.agents/skills/<skill>/SKILL.md` を source of truth として更新する。`.claude/skills/<skill>/SKILL.md` は Claude Code 固有の `allowed-tools` / `argument-hint` を保持する wrapper で、`@${CLAUDE_SKILL_DIR}/../../../.agents/skills/<skill>/SKILL.md` から共通手順を読み込む。

迷ったときは、作業状況から入口を選ぶ:

- 初回セットアップ・上流更新: `/setup`、`/update-paperops`
- セッション再開・進捗記録: `/resume-session`、`/note-writing-session`
- 俯瞰・発散: `/open-paper-scan`
- 関連研究・文献議論: `/source-reach-scan`、`/research-related-work`、`/update-refs`
- 執筆設計・本文調整: `/scientific-gate`、`/design-manuscript-claims`、`/calibrate-claims`、`/paragraph-surgery`、`/polish-ai-draft`
- 結果パターン・AI 初稿の診断・条件文脈化: `/map-result-patterns`、`/audit-ai-draft`、`/contextualize-conditions`
- 日英同期・公開語彙: `/sync-ja-en`、`/public-terminology-pass`
- 通読レビュー: `/start-manuscript-review` で開始し、終了後に `/collect-manuscript-review`、反映時は `/integrate-writing-feedback`
- 査読シミュレーション・返答: `/peer-review-manuscript`、`/respond-to-peer-review`
- 公開前点検: `/review-public-manuscript`、`/figure-story-audit`、`/venue-fit-review`、`/ai-disclosure-check`
- 外部 project link・上流改善: `/resolve-local-paths`、`/feedback-paper-harness`

| スキル | 用途 |
|-------|------|
| `/setup` | 初回プロジェクトセットアップを一括実行 |
| `/resume-session` | 現在の状態を要約し、次のステップを提案 |
| `/note-writing-session` | セッション進捗を記録し、引き継ぎファイルを更新 |
| `/sync-ja-en` | 日本語と英語のブロックを同期 |
| `/update-refs` | 参考文献と参照知識の整合性を検証 |
| `/source-reach-scan` | 外部 Web、GitHub、動画、RSS、SNS などの到達経路と raw capture 方針を整理 |
| `/research-related-work` | 関連研究を調査設計、深掘り、議論、refs 昇格へ整理 |
| `/improve-writing-harness` | プロジェクトローカルの摩擦を特定・修正 |
| `/feedback-paper-harness` | 再利用可能な改善を上流ハーネスにフィードバック |
| `/resolve-local-paths` | `refs/links.toml` と `refs/local/` から外部 link とローカルパスエイリアスを解決 |
| `/update-paperops` | pops 更新通知や上流 paperops scaffold の変更を安全に取り込む |
| `/pull-template-updates` | 旧名。新規作業では `/update-paperops` を使う |
| `/import-manuscript` | 既存 LaTeX 原稿をハーネスにインポート |
| `/open-paper-scan` | 原稿・プロジェクト・ハーネスを俯瞰し、まだ記録や実装に固定しない発散的な違和感と改善案を出す |
| `/map-result-patterns` | raw result、figure data、analysis artifact を result pattern / evidence packet へ抽象化し、claim へ昇格する前の中間層を作る |
| `/scientific-gate` | 中心主張、Abstract、Conclusion、主要図表の claim readiness と人間承認を確認 |
| `/review-public-manuscript` | section / weekly / pre-submit の粒度で、公開原稿だけを入力に外部読者視点の未定義語・ローカル語・暗黙前提をレビュー |
| `/peer-review-manuscript` | 投稿前原稿を査読者パネルと meta-review 形式で評価し、major/minor comment と revision priority を作る |
| `/respond-to-peer-review` | editor / reviewer comments を response matrix、revision plan、response letter 草案へ整理 |
| `/integrate-writing-feedback` | 人間レビューや自然文指示を feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映 |
| `/start-manuscript-review` | TeX 直編集レビュー用 branch を用意し、人間向けの通読ガイドを表示 |
| `/collect-manuscript-review` | TeX diff と inline comment からレビュー台帳を生成し、必要に応じて原稿へ反映 |
| `/design-manuscript-claims` | 作業報告型の原稿を主張中心の構造へ再設計 |
| `/audit-ai-draft` | AI 初稿を公開読者視点と repo 文脈の両方から診断し、論旨設計と改稿計画を作る |
| `/contextualize-conditions` | 条件数、case count、run inventory を claim role と公開条件名へ翻訳 |
| `/calibrate-claims` | evidence strength に合わせて防御的文体と過剰主張を調整 |
| `/polish-ai-draft` | AI 初稿の定型臭を、主張・証拠・開示を保ったまま論文向けに整える |
| `/public-terminology-pass` | ローカル語・内部語・未定義略語を公開語へ置換 |
| `/paragraph-surgery` | 段落単位の flow、topic sentence、stress position を整える |
| `/figure-story-audit` | figure/table の claim, evidence, boundary と本文参照を監査 |
| `/venue-fit-review` | 投稿先・読者モデルに対する title/abstract/構成の fit を点検 |
| `/ai-disclosure-check` | AI 利用ログ、投稿先ポリシー、人間検証、開示文案を点検 |

## リポジトリマップ

```
manuscript/ja/       日本語ソース（% block: ID 付きセクション）
manuscript/en/       英語ミラー（対応するブロック ID）
manuscript/shared/   figures, bib, style
manuscript/mirror/   map.toml, block-ledger.yml, terminology.yml, status.md, change-queue.md
manuscript/venue.md  投稿先情報
manuscript/publication-metadata.toml  公開タイトル、著者、ライセンス、build provenance
submission/          投稿先公式テンプレート、最終提出用 TeX
refs/                知識層: links.toml, summaries, research, source-reach, local（papers, bib, excerpts はスキルが必要時に作成）
_handoff/            人間から AI への未整理ファイル受け取り箱（内容は Git 管理しない）
evidence/            result / figure / source card の正本
claims/              claim / scientific gate / argument card の正本
review/              feedback / review round / response card の正本
requests/            analysis / writing request card の正本
notes/views/         card 正本を人間が俯瞰するビュー
notes/               project-brief, contribution-claims, source-reach, related-work-map, reviewer-model, ai-draft-polish, ai-use, reproducibility, handoff, todo, decision-log, 旧互換ビュー
scripts/             ビルド、TeX 構造、lint、citation-check、skill 対応、ミラー/鮮度/submission チェック、公開語彙・claim-evidence チェック、レビュー回収、エクスポート、コンテキスト収集
.github/ISSUE_TEMPLATE/ 原稿レビュー、エビデンス不足、ハーネス摩擦の収集フォーム
.claude/             settings.json（権限＋deny）、skills wrapper、rules/、hooks/
.agents/             共通 source of truth となる project skills
TROUBLESHOOTING.md   nested repo と safe.directory の注意
```

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、`/feedback-paper-harness` を使用して `Nkzono99/paperops` にルーティングする。
