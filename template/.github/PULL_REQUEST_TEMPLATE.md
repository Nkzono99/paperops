## 概要

原稿またはハーネスの変更内容を記述する。

## チェック項目

- [ ] 執筆状態が変わった場合は `notes/` を更新した
- [ ] バイリンガルコンテンツが変わった場合は `manuscript/mirror/status.md` を更新した
- [ ] 日英同期を確認した場合は `manuscript/mirror/block-ledger.yml` を更新した
- [ ] `make ci` を実行した（参考文献、citation key、ミラー、公開語彙、claim-evidence、ビルド構造）
- [ ] 外部共有・投稿に近い変更の場合は `make pre-submit` を実行し、`manuscript/publication-metadata.toml`、`notes/reproducibility.md`、submission drift を確認した
- [ ] 必要に応じて refs を追加・キュレーションした

## 論文品質チェック

- [ ] この変更で中心主張が強くなったか、または読みやすくなった
- [ ] 新しい主張は `notes/claim-evidence-map.md` に登録した
- [ ] 新しい用語、略語、内部語の置換は `manuscript/mirror/terminology.yml` に登録した
- [ ] 内部 run label / script name / directory name / artifact name が公開本文に残っていない
- [ ] Abstract / Conclusion の主張強度が evidence と一致している
- [ ] Figure caption は claim, evidence, boundary を読者に示している
- [ ] AI が関与した場合は `notes/ai-use.md` を更新した
