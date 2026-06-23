# evidence 層

`evidence/` は raw result や source を本文へ直接流し込む前に、論文上の証拠単位へ整理するカード層である。

- `results/`: 解析結果、simulation result、artifact 由来の result card。
- `figures/`: figure/table がどの claim と boundary を支えるかを記録する card。
- `sources/`: 文献、外部 source、関連研究 finding を claim に接続する前の source card。

正本は各カードであり、`notes/views/` は人間が俯瞰するための集約ビューとして扱う。
