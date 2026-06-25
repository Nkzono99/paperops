# paper-my-topic

`pops init` で作成される個別論文プロジェクトのスターター。

## 初回セットアップ

まず `/setup` を使う。手で進める場合の最小手順は次の通り。

1. リポジトリ名とこの README を実プロジェクト名に合わせる。
2. `uvx --from paper-harness-cli pops setup` と `pops doctor` で `.pops/manifest.toml` と構造を確認する。
3. `refs/links.toml` を調整し、個人環境の実パスは ignored な `refs/local/locations.toml` に書く。
4. 人間から AI へ渡す未整理ファイルは `_handoff/` に置く。
5. `notes/project-brief.md`、`notes/contribution-claims.md`、`manuscript/venue.md`、`manuscript/publication-metadata.toml` を埋める。
6. 必要なら `tex-env.example.toml` を `tex-env.toml` にコピーして TeX 環境を設定する。

`pops` は `uvx --from paper-harness-cli pops ...` で実行する。プロジェクト用 Python 環境が必要な場合だけ `make venv` を使う。

## 日常の流れ

1. `/resume-session` で前回の状態を読む。
2. 今日扱う claim、evidence、feedback、request を確認する。
3. `pops workflow status` と `pops workflow next` で、全体状態と stale section を確認する。
4. 必要なら `contracts/` と `manuscript/writing-profile.yml` を重ね、`paper_ir` と section compiler で Results / Discussion / Methods の読者向け構造を作る。
5. `manuscript/ja/` を中心に書く。
6. 必要な block を `manuscript/en/` に同期する。
7. 人間レビューや自然文の指示は `/integrate-writing-feedback` で feedback card にし、`pops workflow route-review` で戻る深さを決める。
8. 共有前は `make ci` と `make audit`、投稿前は `make pre-submit` を実行する。

## 中間層

- `evidence/`: result / figure / source card の正本
- `claims/`: claim / scientific gate / argument card の正本
- `review/`: feedback / review round / response card の正本
- `requests/`: analysis / writing request card の正本
- `notes/views/`: pure overview view と controlled authoring view
- `contracts/`: section ごとの読者質問、入力、出力、禁止構造
- `workflow/`: 全体状態、section 状態、issue class、stale 伝播
- `manuscript/writing-profile.yml`: 論文種別・投稿先ごとの overlay

旧 `notes/*.md` の一部は互換ビューであり、正本は上のカード層に置く。`paper_ir` は card と controlled view から Writer に渡す context を作る生成一時物であり、手書き正本にはしない。

## 情報の置き場所

- `_handoff/`: 人間から AI へ渡す未整理ファイル。内容は Git 管理しない。
- `_archives/`: 1から書き直すための sealed scratch archive。通常の AI 執筆では読まない。
- `refs/summaries/`: 採用する文献や外部 source の確認済み要約。
- `refs/research/`: 関連研究調査の設計と raw finding。
- `refs/source-reach/`: Web、GitHub、動画、RSS、SNS など外部 source channel の調査メモ。
- `refs/links.toml`: 共有できる外部 project / directory link の意味。
- `refs/imports/`: 外部 export bundle の source index、integrity、claim role、取り込み状態。
- `refs/local/locations.toml`: 個人環境の実パス。Git 管理しない。

過去稿を封印して同じ repo で書き直す場合は、`pops scratch archive`、`pops scratch reset`、`pops scratch restore` を使う。archive は `_archives/` に split bundle として置かれ、通常の skill は参照しない。

`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` に作る作業用ドキュメントは日本語で書く。citation key、TOML field name、外部ツール名などの識別子は英語のままでよい。

## 主要スキル

- `/source-reach-scan`, `/research-related-work`: 外部 source と関連研究を整理する。
- `/map-result-patterns`, `/scientific-gate`: 結果を証拠カードにし、主張として書けるか判定する。
- `/finish-manuscript`: `/goal` で原稿完成まで進め、Writer 前に `paper_ir` と section compiler を通す。
- `/review-public-manuscript`, `/peer-review-manuscript`: 公開原稿や投稿前原稿を読者・査読者目線で読む。
- `/respond-to-peer-review`: 実査読コメントへの返答を整理する。
- `/integrate-writing-feedback`: 人間レビューや指示を上流カードと原稿へ反映する。
- `/open-paper-scan`: まだ記録や実装に固定せず、俯瞰的な違和感や改善案を出す。
- `/feedback-paper-harness`: 再利用可能な摩擦を上流 `paperops` に戻す。

## ディレクトリ

- `manuscript/`: 日英原稿、共有アセット、ミラー制御、投稿先情報
- `contracts/`: Introduction / Methods / Results / Discussion / Conclusion の入出力契約
- `workflow/`: 階層型状態機械、現在状態、review round summary、人間判断
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX
- `refs/`: 文献、外部 source、外部 link、ローカルパス alias
- `evidence/`, `claims/`, `review/`, `requests/`: 論文を書く前後のカード層
- `notes/`: project brief、読者モデル、AI 利用、再現性、handoff、decision log、views
- `.agents/`, `.claude/`: Agent / Claude Code 用 skill
- `scripts/`: 検証、ビルド、レビュー回収、ミラー確認
- `TROUBLESHOOTING.md`: nested repo や Windows safe.directory などの注意
