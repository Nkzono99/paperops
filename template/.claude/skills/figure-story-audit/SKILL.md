---
name: figure-story-audit
description: figure/table が claim, evidence, boundary を支えているか、caption・本文参照・claim-evidence map を監査する。
argument-hint: "[figure-or-section]"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

# figure-story-audit

図表を結果の置き場ではなく、主張を支える証拠として監査する。

## 最初に読むファイル

- `notes/claim-evidence-map.md`
- 対象の figure/table caption
- caption を参照する本文 block
- `notes/reproducibility.md`

## 手順

1. 各 figure/table について、figure claim、panel evidence、boundary、uncertainty を整理する。
2. 本文参照が figure の takeaway と一致しているか確認する。
3. caption に sample/condition/scope/statistics が不足していないか確認する。
4. `notes/claim-evidence-map.md` の Figure/table 欄を更新する。
5. 図表 provenance が必要なら `notes/reproducibility.md` に追記する。

## 出力

- Figure/table story map
- Caption rewrite plan
- Body reference fixes
- Claim-evidence map updates
- Reproducibility updates
