# paper-my-topic

`pops init` で `paperops` から構築された個別論文プロジェクトのスターターリポジトリ。

## 初回使用前

`/setup` スキルで以下の手順を一括実行できる:

1. リポジトリ名を変更し、この README を更新する。
2. `uvx --from paper-harness-cli pops setup` / `doctor` で `.pops/manifest.toml` とハーネス状態を確認する。
3. `refs/links.toml` で外部 project / directory への共有 link を調整し、`refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーして実パスをユーザー自身で記入する。
4. 人間から AI に渡す未整理ファイルがある場合は `_handoff/` に置き、必要なものを `refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` に整理する。
5. `tex-env.example.toml` を `tex-env.toml` にコピーし、TeX 環境を設定する（任意）。
6. `.github/workflows/*.yml` 内のプレースホルダーワークフロー参照を、実際の `paperops` リポジトリパスに置き換える。
7. `evidence/`、`claims/`、`review/`、`requests/` の card template と `notes/views/` を確認し、`manuscript/publication-metadata.toml`、`notes/project-brief.md`、`notes/source-reach.md`、`notes/related-work-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/venue.md`、`notes/contribution-claims.md`、`notes/reproducibility.md` を記入する。

## 基本ワークフロー

1. `resume-session` で開始する。
2. `claims/`、`evidence/`、`review/feedback/`、`requests/` と `notes/views/` で、今日の block が扱う claim readiness、result pattern、claim、読者の懸念を確認する。
3. 関連研究や外部情報源を集める場合は、必要に応じて `/source-reach-scan` で source channel と raw capture 方針を決めてから、`/research-related-work` で `refs/research/` の調査設計、`notes/related-work-map.md` の議論、`refs/summaries/` への昇格を分ける。
4. `manuscript/ja/` で執筆または改訂する。
5. 新しい公開用語や内部語の置換が必要なら `manuscript/mirror/terminology.yml` に記録する。
6. 必要なブロックを `manuscript/en/` にミラーし、確認済み同期後に `python scripts/mirror-freshness-check.py --root manuscript --update` で ledger を更新する。投稿前は `make mirror-strict-check` または `make pre-submit` で freshness warning を残さない。
7. 通読レビューでは `/start-manuscript-review` で review branch と inline comment ルールを確認し、終了後に `/collect-manuscript-review` で TeX diff と comment を台帳化する。
8. 1 節を書いた直後や週次レビューでは `/review-public-manuscript` を `section` / `weekly` として使い、公開原稿だけで読者が詰まる語彙・前提・figure story を確認する。
9. 投稿前に査読者目線で厳しく読む場合は `/peer-review-manuscript`、実際の editor / reviewer comments に返答する場合は `/respond-to-peer-review` で `review/` のカードと `notes/views/peer-review.md` へ整理する。
10. 人間が原稿レビューやプロンプト指示を出した場合は `/integrate-writing-feedback` で feedback card にし、claim / gate / evidence / request / manuscript へ遡って反映する。
11. 投稿先公式テンプレートへ展開する段階では `submission/<venue>/` を使い、`manuscript/` と混ぜない。
12. `notes/` に進捗を記録し、AI が文献・解析・図表・投稿文面・査読返答に関与した場合は `notes/ai-use.md` も更新する。
13. 主要な変更を共有する前に `make ci` を実行し、参考文献、citation key、ミラー、block freshness、公開語彙、claim-evidence、カード層、skill 対応、ビルド構造を確認する。
14. 投稿・外部共有の直前には `make pre-submit` を実行し、引用サマリー、公開メタデータ、再現性メモ、submission slot、submission drift、workflow 参照、スタータープレースホルダーの残存を確認する。

既存原稿がある場合は `/import-manuscript` でインポートできる。

`pops` は `uvx --from paper-harness-cli pops ...` で実行する。複数 version を跨ぐ更新は `uvx --from paper-harness-cli pops update-paperops --plan` で chain を確認する。ローカルワークフローは Python 3.11 以上の `.venv/bin/python` / `.venv/Scripts/python.exe` を優先し、`.venv` が無い場合は Makefile とビルドヘルパーが利用可能な Python 3.11 以上の interpreter を探索する。

外部 project やローカルディレクトリを論文に紐づける場合は `refs/links.toml` を共有台帳として使う。実パスは ignored な `refs/local/locations.toml` に分離し、確認には `uvx --from paper-harness-cli pops links check` または `make links-check` を使う。`kind = "runops_project"` の link は runops MCP / publication export manifest から結果や図表候補を調べる入口として扱う。追加解析・図表・追加実験が必要になったら `requests/analysis/` に記録し、`notes/views/research-requests.md` で俯瞰し、`runops.paper.request.draft` で検証してから runops project の `research/paper_requests.toml` へ handoff する。

`_handoff/` は人間から AI へ渡す未整理ファイルの一時受け取り箱である。内容は既定で Git 管理されない。AI は、残す価値のある情報を `refs/summaries/`、`evidence/`、`claims/`、`review/feedback/`、`requests/`、`refs/links.toml`、`notes/handoff.md`、`notes/reproducibility.md` などへ整理し、秘密情報や個人環境の絶対パスを tracked ファイルへ移さない。

`refs/`、`evidence/`、`claims/`、`review/`、`requests/`、`notes/` に作る作業用ドキュメントは日本語で書く。citation key、TOML field name、投稿先指定、外部ツール名などの識別子は英語のままでよい。関連研究を広く集める場合は `/research-related-work` で `refs/research/` に調査設計を置き、採用する文献だけ `refs/summaries/` と `.bib`、必要なら `evidence/sources/` へ昇格する。外部 Web、GitHub、動画、RSS、SNS、議論サイトを使う場合は `/source-reach-scan` で `notes/source-reach.md` と `refs/source-reach/` に到達経路と raw capture 方針を分ける。査読シミュレーションや実査読返答は `/peer-review-manuscript` と `/respond-to-peer-review` で `review/` のカードに要約と対応 ID を残し、raw correspondence は `_handoff/` やローカル入力に留める。simulation results や figure data を本文に入れる前に、必要なら `/map-result-patterns` で `evidence/results/` と `evidence/figures/` のカードに result pattern / evidence packet として束ねる。中心主張、Abstract、Conclusion、主要図表に使う claim は `/scientific-gate` で `claims/gates/` の gate card と `notes/views/scientific-gate.md` の readiness を確認する。AI 初稿が条件数の列挙や防御的な caveat に寄りすぎた場合は `/map-result-patterns`、`/audit-ai-draft`、`/contextualize-conditions` で card と `notes/views/` を更新してから本文を直す。claim lock 後に機械的な文体だけを直す場合は `/polish-ai-draft` を使い、AI 利用開示を消さない。

構成、読者体験、執筆ハーネスの違和感をまだ修正や記録に固定せず広げたい場合は `/open-paper-scan` を使う。出た idea はその場では採用せず、必要になったものだけ後で `/scientific-gate`、`/source-reach-scan`、`/map-result-patterns`、`/audit-ai-draft`、`/design-manuscript-claims`、`/improve-writing-harness`、`/feedback-paper-harness` へ渡す。

`tex-env.toml` では TeX Live / Docker だけでなく、JA / EN ごとの `latexmk` mode と engine も設定できる。日本語ドラフトで `uplatex + dvipdfmx` が必要な場合は、`tex-env.example.toml` の `[latex.ja]` 例をコピーする。

Windows / PowerShell で PDF を確認したい場合は、TeX Live の代わりに pinned Tectonic を `.tools/` に取得してビルドできる:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-ja-pdf.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-en-pdf.ps1
```

ネットワーク取得を禁止したい場合は `-NoDownload` を付ける。この場合、既に `.tools/` に取得済みの Tectonic または PATH 上の `tectonic.exe` が必要になる。

## テンプレートフィードバック

繰り返しのハーネス摩擦を見つけた場合、`/feedback-paper-harness` または `pops feedback` で再利用可能な改善をソースリポジトリ `Nkzono99/paperops` に戻す。

## トラブルシューティング

nested private repo 運用や Windows の dubious ownership で git 操作が止まる場合は、[TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照する。

## ディレクトリの概要

- `manuscript/`: バイリンガルソース、共有アセット、ミラー制御、投稿先情報
- `manuscript/publication-metadata.toml`: 公開タイトル、著者、ライセンス、最後に共有した build provenance
- `submission/`: 投稿先公式テンプレートと最終提出用 TeX の分離スロット
- `refs/`: 参照知識、サマリー、関連研究の調査設計、外部 source reach、外部 link 台帳、ローカルパスエイリアス（raw PDF は `refs/papers/` に置いても既定で ignore し、共有時は `refs/summaries/` を優先）
- `_handoff/`: 人間から AI へ渡す未整理ファイルの一時受け取り箱（内容は Git 管理しない）
- `evidence/`: result / figure / source card の正本
- `claims/`: claim / scientific gate / argument card の正本
- `review/`: feedback / review round / response card の正本
- `requests/`: analysis / writing request card の正本
- `notes/`: プロジェクト概要、貢献主張、source reach、related-work map、読者モデル、AI 初稿 polish、AI 利用ログ、再現性メモ、引き継ぎ、意思決定、`notes/views/` の俯瞰ビュー
- `.github/ISSUE_TEMPLATE/`: 原稿レビュー、エビデンス不足、ハーネス摩擦の収集フォーム
- `.claude/`: プロジェクトローカルの設定、スキル、ルール、フック
- `.agents/`: Codex 用のプロジェクトローカルスキル互換入口
- `scripts/`: 軽量な検証・TeX 構造/skill 対応・ミラー鮮度/submission drift・公開語彙/claim-evidence チェック・レビュー回収・パッケージングヘルパー
- `TROUBLESHOOTING.md`: nested repo、Windows safe.directory などの運用注意
