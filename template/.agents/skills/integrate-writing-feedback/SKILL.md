---
name: integrate-writing-feedback
description: Use when routing manuscript, human, reviewer, or PDF feedback back to paper cards.
---

# integrate-writing-feedback

人間は原稿レベルのレビューや自然文の指示だけを出せばよい。この skill は、その指示を `review/feedback/` の feedback card に変換し、必要な上流カードを更新してから本文へ反映する。

## 入力

- ユーザーのプロンプト指示。
- PDF / TeX / section / block への人間レビュー。
- `/collect-manuscript-review` が作った review ledger。
- `/peer-review-manuscript` や `/respond-to-peer-review` の concern / comment。

raw confidential text は `_handoff/` やローカル入力に留め、tracked card には要約、comment ID、対象 block、route、prose explanation を残す。

`_archives/` は feedback source にしない。過去稿からの復元や比較は、ユーザーが明示した場合だけ `pops scratch` 経由で扱う。

## 先に読む

1. `manuscript/mirror/status.md`
2. 対象の `manuscript/ja/` または `manuscript/en/` block
3. `review/README.md`
4. `review/feedback/`
5. `notes/views/claim-evidence-map.md`
6. `notes/views/scientific-gate.md`
7. 必要に応じて `claims/claims/`、`claims/gates/`、`evidence/`、`requests/`

旧下流で `notes/views/` がまだ無い場合だけ、旧互換の `notes/claim-evidence-map.md`、`notes/scientific-gate.md`、`notes/result-pattern-map.md` を読む。

## 手順

1. 指摘を 1 論点 1 feedback card に分ける。ファイル名は `review/feedback/FB-YYYYMMDD-short-slug.md` など、衝突しないものにする。
2. `review/feedback/feedback-card-template.md` の front matter を使い、`target`、`issue_type`、`severity`、`upstream_routes` を埋める。
3. 本文だけで済むか、上流へ戻すべきかを判定する。
   - overclaim、主張の順序、caveat の格上げ/格下げ: `claim_scope_change`、必要なら `scientific_gate_reopen`
   - 数値、分母、条件名、図表の読み: `result_card_update` または `figure_card_update`
   - 関連研究、反論、引用不足: `source_card_update`
   - 追加解析、再計算、感度分析: `analysis_request`
   - block 単位の改稿: `writing_request`
   - 誤字、語調、読みやすさだけ: `manuscript_only`
4. `upstream_routes` の順に更新する。本文編集は最後に行う。
5. claim / gate / evidence を更新した場合は、対応する `notes/views/` も更新する。旧 `notes/*.md` は互換ビューなので、正本として新規情報を書き込まない。
6. 追加作業が必要なら `requests/analysis/` または `requests/writing/` に request card を作る。
7. 原稿を直す場合は `manuscript/mirror/status.md` の source-of-truth 言語を尊重し、`% block:` ID を保持する。
8. route/status label は field として保持してよいが、隣に prose explanation を書く。何を前提に、どの evidence / claim / figure に遡り、本文 claim へどう影響するかを一文で説明する。
9. 解決済み feedback card は `status: resolved` にし、反映ログへ更新 card、本文 block、検証コマンドを書く。未解決なら `status: open` のまま route と closure blocker を明確にする。

## 出力

- `Feedback cards`: 作成/更新した card
- `Upstream changes`: claim / gate / evidence / request の更新
- `Manuscript edits`: 編集した block
- `Views updated`: 更新した `notes/views/`
- `Validation`: 実行したコマンド
- `Remaining open feedback`: 未解決の card と理由
- `Route explanations`: route/status label と prose explanation

## 注意

- 人間の「ここを直して」という指示を、本文だけの局所修正に固定しない。
- `analysis-needed` や `assumption-blocked` の claim を、文体だけで `ready-to-write` に見せない。
- feedback card には raw confidential comment を長く貼らず、要約と ID を残す。
- 人間承認が必要な assumption は AI が勝手に受容しない。

## Codex 実行メモ

- 最初に `rg "^% block:" manuscript/ja manuscript/en` で対象 block を探す。
- 作成する card は既存 ID と衝突しないよう `rg "^id: FB-" review/feedback` で確認する。
- 本文を編集したら `make mirror-check` を実行する。claim / evidence / layer card を更新したら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。
