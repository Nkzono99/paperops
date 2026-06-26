---
name: finalize-manuscript
description: Use before declaring a manuscript goal complete or before preparing the final share, submission, or response package.
---

# finalize-manuscript

`finish-manuscript` の最後に、本文内容、review loop、mirror、引用、figure、submission readiness をまとめて確認する skill。`pre-submit` は STRUCTURE_ACCEPTED 後の最終確認であり、本文 blocker の代替ではない。

## Finish criteria

次を満たすまで `/goal` を完了にしない。

- 中心主張、Abstract、Conclusion、main figure caption の claim が `scientific-gate` で `ready-to-write` または人間が明示承認した scope になっている。
- `_paperops/notes/views/storyline.md` が埋まり、`storyline_architecture_approved`、Results hierarchy、Discussion functions が確認されている。
- human approval が必要な assumption、投稿先、claim scope、response stance が未承認のまま残っていない。
- `_paperops/review/feedback/` と reviewer loop に blocking / major の open item が残っていない。残す場合は defer 理由と本文での scope limit がある。
- 図表、caption、本文参照、claim-evidence map、related work、AI disclosure、reproducibility の不整合が解消されている。
- Results / Discussion が `section_depth` の soft floor を満たすか、short_article profile または人間承認済みの例外として記録されている。
- 概念語ビューで accepted / plain-language / avoid が整理され、表記揺れや過剰な concept-term compression が残っていない。
- 実査読改訂では、comment inventory、response matrix、本文変更、response letter が対応している。
- 最終 PDF / TeX / response letter のどれを成果物とするかを明示し、最終 commit または共有すべき artifact を記録している。

## Checks

完了前は `make finish-manuscript-check` を実行する。原稿を編集したら `make mirror-check`、引用や bibliography に触れたら `make citation-check`、概念語に触れたら `make concept-term-check`、図表に触れたら `make figure-reference-check` と `make figure-obligation-check`、claim / evidence / layer card に触れたら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。

storyline を更新したら `make storyline-check` を実行する。投稿前には `scripts/check-storyline.py --root . --strict`、`scripts/check-figure-obligations.py --root . --strict`、`make pre-submit` を使う。

AI が本文、レビュー、response draft に関与した場合は `ai-disclosure-check` を通す。文章を磨くために evidence の弱さを隠さない。`analysis-needed` や `assumption-blocked` は文体ではなく upstream route で処理する。

raw confidential reviewer text を web 検索語、Issue、公開 PR、tracked notes に入れない。共有前に成果物、未解決 blocker、defer した hygiene、次の人間判断を短く列挙する。
