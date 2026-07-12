---
name: integrate-writing-feedback
description: Use when routing manuscript, human, reviewer, or PDF feedback back to paper cards.
---

# integrate-writing-feedback

人間は原稿レベルのレビューや自然文の指示だけを出せばよい。この skill は、その指示を `_paperops/model/issues/feedback/` の feedback card に変換し、必要な上流カードを更新してから本文へ反映する。

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
3. `_paperops/model/issues/README.md`
4. `_paperops/model/issues/feedback/`
5. `_paperops/notes/views/claim-evidence-map.md`
6. `_paperops/notes/views/scientific-gate.md`
7. 必要に応じて `_paperops/model/research/claims/`、`_paperops/model/research/gates/`、`_paperops/model/research/`、`_paperops/model/issues/`

旧下流で `_paperops/notes/views/` がまだ無い場合だけ、旧互換の `_paperops/notes/claim-evidence-map.md`、`_paperops/notes/scientific-gate.md`、`_paperops/notes/result-pattern-map.md` を読む。

## 手順

1. 指摘を1論点1recordに分ける。v2-authoritativeではIssue Modelの`workflow_issue`（`ISS-*`）を使い、review roundは`issue_refs`で束ねる。legacy modeでは従来のfeedback cardを使う。
2. `_paperops/model/issues/feedback/feedback-card-template.md` の front matter を使い、`target`、`issue_type`、`severity`、`upstream_routes` を埋める。
3. 本文だけで済むか、上流へ戻すべきかを判定する。
   - overclaim、主張の順序、caveat の格上げ/格下げ: `claim_scope_change`、必要なら `scientific_gate_reopen`
   - story spine、reader promise、claim order、Abstract / Results / Discussion / Conclusion の scope ずれ: `storyline_change`
   - Results が図表・条件・実施順の列挙になっている: `results_hierarchy_gap`
   - Discussion が limitation 羅列で、機構・先行研究差分・次の検証がない: `discussion_function_gap`
   - Results / Discussion の薄さが段落修正では済まない: `section_depth_blocker`
   - 数値、分母、条件名、図表の読み: `result_card_update` または `figure_card_update`
   - 関連研究、反論、引用不足: `source_card_update`
   - 追加解析、再計算、感度分析: `analysis_request`
   - block 単位の改稿: `writing_request`
   - 投稿前 metadata / license / venue formatting だけ: `submission_hygiene_only`。STRUCTURE_ACCEPTED 前は主作業にしない。
   - 誤字、語調、読みやすさだけ: `manuscript_only`
4. `upstream_routes` の順に更新する。本文編集は最後に行う。
5. claim / gate / evidence を更新した場合は、対応する `_paperops/notes/views/` も更新する。旧 `_paperops/notes/*.md` は互換ビューなので、正本として新規情報を書き込まない。
6. 追加作業が必要なら `_paperops/model/issues/analysis/` または `_paperops/model/issues/writing/` に request card を作る。
7. 原稿を直す場合は `manuscript/mirror/status.md` の source-of-truth 言語を尊重し、`% block:` ID を保持する。
8. route/status label は field として保持してよいが、隣に prose explanation を書く。何を前提に、どの evidence / claim / figure に遡り、本文 claim へどう影響するかを一文で説明する。
9. v2-authoritativeの定型route / closureは`pops workflow issue route|close|reopen`でplan化し、`pops workflow apply <plan-id> --yes`だけが反映する。解決済みIssueはverification refを伴って個別にcloseする。legacy feedback cardは従来どおり`status: resolved`へ更新する。

## 出力

- `Feedback cards`: 作成/更新した card
- `Upstream changes`: claim / gate / evidence / request の更新
- `Manuscript edits`: 編集した block
- `Views updated`: 更新した `_paperops/notes/views/`
- `Validation`: 実行したコマンド
- `Remaining open feedback`: 未解決の card と理由
- `Route explanations`: route/status label と prose explanation

## 注意

- 人間の「ここを直して」という指示を、本文だけの局所修正に固定しない。
- `storyline_change`、`section_depth_blocker`、`results_hierarchy_gap`、`discussion_function_gap` は `manuscript_only` より上位に扱う。
- `submission_hygiene_only` は content blocker が閉じた後だけ本文完了作業として扱う。
- `analysis-needed` や `assumption-blocked` の claim を、文体だけで `ready-to-write` に見せない。
- feedback card には raw confidential comment を長く貼らず、要約と ID を残す。
- 人間承認が必要な assumption は AI が勝手に受容しない。

## Codex 実行メモ

- 最初に `rg "^% block:" manuscript/ja manuscript/en` で対象 block を探す。
- 作成する card は既存 ID と衝突しないよう `rg "^id: FB-" review/feedback` で確認する。
- 本文を編集したら `make mirror-check` を実行する。claim / evidence / layer card を更新したら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
