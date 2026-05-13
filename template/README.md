# paper-my-topic

`pops init` で `paperops` から構築された個別論文プロジェクトのスターターリポジトリ。

## 初回使用前

`/setup` スキルで以下の手順を一括実行できる:

1. リポジトリ名を変更し、この README を更新する。
2. `uvx --from paper-harness-cli pops setup` / `doctor` で `.pops/manifest.toml` とハーネス状態を確認する。
3. `refs/local/locations.example.toml` を `refs/local/locations.toml` にコピーし、ローカルパスはユーザー自身で記入する。
4. `tex-env.example.toml` を `tex-env.toml` にコピーし、TeX 環境を設定する（任意）。
5. `.github/workflows/*.yml` 内のプレースホルダーワークフロー参照を、実際の `paperops` リポジトリパスに置き換える。
6. `manuscript/publication-metadata.toml`、`notes/project-brief.md`、`notes/claim-evidence-map.md`、`notes/reviewer-model.md`、`notes/ai-use.md`、`manuscript/venue.md`、`notes/contribution-claims.md`、`notes/reproducibility.md` を記入する。

## 基本ワークフロー

1. `resume-session` で開始する。
2. `notes/claim-evidence-map.md` と `notes/reviewer-model.md` で、今日の block が支える claim と読者の懸念を確認する。
3. `manuscript/ja/` で執筆または改訂する。
4. 新しい公開用語や内部語の置換が必要なら `manuscript/mirror/terminology.yml` に記録する。
5. 必要なブロックを `manuscript/en/` にミラーし、確認済み同期後に `python scripts/mirror-freshness-check.py --root manuscript --update` で ledger を更新する。
6. 通読レビューでは `/start-manuscript-review` で review branch と inline comment ルールを確認し、終了後に `/collect-manuscript-review` で TeX diff と comment を台帳化する。
7. 1 節を書いた直後や週次レビューでは `/review-public-manuscript` を `section` / `weekly` として使い、公開原稿だけで読者が詰まる語彙・前提・figure story を確認する。
8. 投稿先公式テンプレートへ展開する段階では `submission/<venue>/` を使い、`manuscript/` と混ぜない。
9. `notes/` に進捗を記録し、AI が文献・解析・図表・投稿文面に関与した場合は `notes/ai-use.md` も更新する。
10. 主要な変更を共有する前に `make ci` を実行し、参考文献、citation key、ミラー、block freshness、公開語彙、claim-evidence、skill 対応、ビルド構造を確認する。
11. 投稿・外部共有の直前には `make pre-submit` を実行し、引用サマリー、公開メタデータ、再現性メモ、submission slot、submission drift、workflow 参照、スタータープレースホルダーの残存を確認する。

既存原稿がある場合は `/import-manuscript` でインポートできる。

`pops` は `uvx --from paper-harness-cli pops ...` で実行する。複数 version を跨ぐ更新は `uvx --from paper-harness-cli pops update-paperops --plan` で chain を確認する。ローカルワークフローは Python 3.11 以上の `.venv/bin/python` / `.venv/Scripts/python.exe` を優先し、`.venv` が無い場合は Makefile とビルドヘルパーが利用可能な Python 3.11 以上の interpreter を探索する。

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
- `refs/`: 参照知識、サマリー、ローカルパスエイリアス（raw PDF は `refs/papers/` に置いても既定で ignore し、共有時は `refs/summaries/` を優先）
- `notes/`: プロジェクト概要、貢献主張、claim-evidence map、読者モデル、AI 利用ログ、再現性メモ、引き継ぎ、意思決定の追跡
- `.github/ISSUE_TEMPLATE/`: 原稿レビュー、エビデンス不足、ハーネス摩擦の収集フォーム
- `.claude/`: プロジェクトローカルの設定、スキル、ルール、フック
- `.agents/`: Codex 用のプロジェクトローカルスキル互換入口
- `scripts/`: 軽量な検証・TeX 構造/skill 対応・ミラー鮮度/submission drift・公開語彙/claim-evidence チェック・レビュー回収・パッケージングヘルパー
- `TROUBLESHOOTING.md`: nested repo、Windows safe.directory などの運用注意
