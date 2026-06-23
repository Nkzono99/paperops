# claims 層

`claims/` は論文の主張、科学的ゲート、論旨構造のカード正本を置く層である。

- `claims/`: claim card。本文で言う内容、scope、limitation、依存する evidence を保持する。
- `gates/`: scientific gate card。Abstract、Conclusion、主要図表へ進めてよいかを判定する。
- `arguments/`: argument card。複数 claim の順序、読者モデル、反論処理を設計する。

`notes/claim-evidence-map.md` などの旧ノートは互換ビューであり、正本はこの層のカードである。
