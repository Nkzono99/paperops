# アーキテクチャ

このリポジトリはテンプレート保守の関心事と個別論文の執筆関心事を分離している。

## 層構成

### 1. テンプレートリポジトリ層

リポジトリルートは、すべての下流論文リポジトリで共有すべきアセットを管理する:

- 再利用可能な GitHub ワークフロー
- テンプレート改善のための Issue フォーム
- テンプレート保守者向けスキル
- `pops` CLI によるスキャフォールド初期化、診断、ハーネス更新
- 変更履歴とガバナンスドキュメント
- CLI パッケージとして `template/` を bundled scaffold に含めるための配布設定

この層は意図的に小さく安定している。ハーネスを安全に進化させることが役割である。

### 2. 個別論文スキャフォールド層

`template/` は個別原稿リポジトリの完全な構造を含む。
このスキャフォールドには以下が含まれる:

- `ja/` と `en/` に分割された原稿ソース
- `manuscript/mirror/` 配下のミラー制御層と block freshness ledger
- `refs/` 配下の参照知識、関連研究の調査設計、外部 source reach、外部 link 台帳。raw PDF は `refs/papers/` でローカル保持しても既定では ignore し、共有知識は `refs/summaries/`、関連研究の raw exploration は `refs/research/`、外部 source channel の raw capture は `refs/source-reach/`、外部 project / directory の共有意図は `refs/links.toml` に集約する。作業用ドキュメントは日本語で書く
- `evidence/` 配下の result / figure / source card。raw result や外部 source を本文へ直接入れず、claim に接続できる証拠単位へ束ねる。作業用ドキュメントは日本語で書く
- `claims/` 配下の claim / scientific gate / argument card。中心主張、scope、limitation、readiness、論旨順序の正本を保持する。作業用ドキュメントは日本語で書く
- `review/` と `requests/` 配下の feedback / review round / response / analysis request / writing request card。人間の原稿レビューやプロンプト指示を、本文だけでなく claim / gate / evidence へ遡らせる
- `notes/` 配下のセッション継続性ノート、外部ソース到達メモ、関連研究マップ、読者モデル、AI 初稿 polish、AI 利用ログ、`notes/views/` の俯瞰ビュー。旧 `notes/*.md` の一部は互換ビューであり、正本はカード層に置く
- `manuscript/publication-metadata.toml`、`notes/ai-use.md`、`notes/reproducibility.md` による公開メタデータ・AI 利用ログ・再現性メモ
- `submission/<venue>/` 配下の投稿先公式テンプレートと最終提出用 TeX
- 下流論文リポジトリ用の GitHub Issue フォーム
- プロジェクトローカルの Claude / Codex スキルとフック
- ビルド、TeX 構造、lint、citation key 検証、skill 対応、エクスポート、ノート収集、投稿前 readiness 確認のための軽量スクリプト

## 設計原則

- 原稿リポジトリを自己記述的に保つ。
- アドホックな翻訳に頼らず、日英のドリフトを明示的に追跡する。
- エイリアスと ignored な設定ファイルによりローカルパスを保存する。
- paper draft から runops project や一般ディレクトリを参照する場合、共有 link metadata と個人環境の絶対パスを分離する。
- runops project link ではローカルパス直読みより MCP の read / inspect / plan tool を優先し、追加要望は `runops.paper.request.draft` で検証してから handoff する。
- 関連研究の探索は、調査対象と field framework を先に固定し、raw search findings を `refs/research/` に留め、採用する文献だけ `refs/summaries/`、`.bib`、`notes/related-work-map.md` に昇格する。
- 外部 Web、GitHub、動画、RSS、SNS、議論サイトは source channel と credential need を先に分け、raw capture を `refs/source-reach/` に留め、確認済み finding だけ `notes/source-reach.md`、`refs/summaries/`、`notes/related-work-map.md` へ昇格する。
- 査読シミュレーションと実査読返答は、raw correspondence と対応台帳を分離し、tracked な `review/feedback/`、`review/responses/`、`notes/views/peer-review.md` には要約、comment ID、revision route を中心に残す。
- simulation results や figure data は本文へ直接流し込まず、まず `evidence/results/` と `evidence/figures/` のカードとして観察単位、条件文脈、claim role へ抽象化する。
- 中心主張、Abstract、Conclusion、主要図表は `claims/gates/` の gate card と `notes/views/scientific-gate.md` で evidence、assumption、reproducibility、人間承認の準備状態を確認してから本文へ渡す。
- 原稿への人間フィードバックは `review/feedback/` の feedback card にし、`upstream_routes` に従って claim scope、scientific gate、result / figure / source card、analysis / writing request、最後に manuscript block へ反映する。
- 共有・投稿時に、公開メタデータ、再現性、図表 provenance、workflow 設定の未記入を検出する。
- 再利用可能な自動化は各論文リポジトリではなくテンプレートリポジトリに集約する。
- CLI は `template/` を source of truth として展開し、下流プロジェクト固有の原稿・notes・refs を自動上書きしない。
- 下流作成は `pops init` に統一する。
- 検証はインタラクティブセッションと CI の両方で実行できる速度を維持する。

## 外部 project link の情報境界

`refs/links.toml` は下流リポジトリで共有できる link の意味だけを持つ。実パス、ホスト名、ユーザー固有の配置は ignored な `refs/local/locations.toml` に置く。これにより、paper draft は runops project や一般ディレクトリを参照できるが、リポジトリには移植不能な絶対パスを混ぜない。

runops project の成果物は、まず publication export、analysis artifact、survey summary などの structured output を MCP 経由で読む。paper 側で追加解析・図表・実験要望が発生した場合は、`requests/analysis/` に paper 文脈を残し、`notes/views/research-requests.md` で俯瞰してから、runops 側の `research/paper_requests.toml` へ request として戻す。
