---
name: venue-fit-review
description: manuscript/venue.md と投稿先・読者モデルに照らして、章立て、title/abstract、scope、必須要件を調整する。
---

# venue-fit-review

投稿先・article type・読者モデルに対して原稿の fit を点検する。

## 最初に読むファイル

- `manuscript/venue.md`
- `notes/reviewer-model.md`
- `notes/claim-evidence-map.md`
- title / abstract / introduction / conclusion
- `submission/<venue>/README.md` があれば読む

## 手順

1. venue、article type、page budget、required sections を整理する。
2. title / abstract / introduction が target reader に約束する contribution を確認する。
3. Methods / Results / Discussion の重心が venue expectation に合うか確認する。
4. 不足する required section、Data/Code availability、AI disclosure、supplement 方針を列挙する。
5. `manuscript/venue.md` と `notes/reviewer-model.md` を更新する。

## 注意

投稿先ポリシーや最新の author guideline が必要な場合は、ユーザーに公式 URL/PDF を渡してもらうか、利用可能な環境で公式情報を確認する。推測で最新ルールを断定しない。

## 出力

- Venue fit summary
- Required changes
- Reader expectation gaps
- Files updated
- Open questions

## Codex 実行メモ

- `manuscript/venue.md`、`notes/reviewer-model.md`、`notes/claim-evidence-map.md` を読む。
- 最新投稿規定は推測せず、公式 URL/PDF が必要なら確認する。
- 必要なら `manuscript/venue.md` と `notes/reviewer-model.md` を更新する。
