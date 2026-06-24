# 外部 bundle import state

外部 project の export bundle を、図表・CSV・claim evidence として使う前にここへ import state を記録する。

`refs/links.toml` は「どの外部 project / directory を参照するか」を表す。`refs/imports/*.toml` は、その link から取り込む bundle がどの provenance state にあるかを表す。

## 状態

- `script_only_candidate`: script や focused test だけがある候補。paper 側では evidence にしない。
- `import_hook_candidate`: import/readiness hook に名前が出たが、export / index / integrity がまだ揃っていない候補。
- `dirty_integrated_candidate`: dirty worktree 上で生成物や hook は揃い始めたが、source commit が固定されていない候補。
- `dirty_indexed_candidate`: dirty worktree 上の source index / integrity manifest には入ったが、tracked export ではない候補。
- `tracked_indexed_export`: source commit、export copy、source index、integrity manifest が揃った bundle。
- `paper_imported_state`: paper repo 側で分類・要約・claim routing まで反映した状態。
- `rejected_or_discarded`: 今回の paper では使わないと判断した候補。

## 運用

1. `import-state-template.toml` を `refs/imports/<link-id>-<bundle>.toml` へコピーする。
2. `link_id` は `refs/links.toml` の id に合わせる。
3. `source_index` と `integrity_manifest` は、外部 bundle 内の相対パスと row count を記録する。
4. `artifact_category_summary`、`claim_evidence_policy`、`must_not_claim` で、物理 evidence、authoring guard、provenance QA、notes-only を混同しない。
5. 図表・本文・claim card に接続する前に `make external-import-check` を実行する。

個人環境の絶対パスはここに書かない。実パスは ignored な `refs/local/locations.toml` に置く。
