---
name: finalize-manuscript
description: Use before declaring a manuscript goal complete or before preparing the final share, submission, or response package.
---

# finalize-manuscript

`finish-manuscript` の最後に、本文内容、review loop、mirror、引用、figure、submission readiness をまとめて確認する skill。`pre-submit` は STRUCTURE_ACCEPTED 後の最終確認であり、本文 blocker の代替ではない。

`manuscript/` は living authoring source であり、投稿後や査読後も revision-authoring に戻って編集できる。投稿・外部共有・再投稿の直前だけ、`submission-gate` で submission candidate / round snapshot を作れる状態か確認する。

## Finish criteria

次を満たすまで `/goal` を完了にしない。

- 中心主張、Abstract、Conclusion、main figure caption の claim が `scientific-gate` で `ready-to-write` または人間が明示承認した scope になっている。
- `_paperops/notes/views/storyline.md` が埋まり、`storyline_architecture_approved`、Results hierarchy、Discussion functions、Methods definition registry が確認されている。
- human approval が必要な assumption、投稿先、claim scope、response stance が未承認のまま残っていない。
- `_paperops/model/issues/feedback/` と reviewer loop に blocking / major の open item が残っていない。残す場合は defer 理由と本文での scope limit がある。
- 図表、caption、本文参照、claim-evidence map、related work、AI disclosure、reproducibility の不整合が解消されている。
- Results / Discussion が `section_depth` の soft floor を満たすか、short_article profile または人間承認済みの例外として記録されている。
- Results の baseline / comparator rationale と、Methods の estimand / decision criteria / verification 定義が本文の公開読者に見える。
- 概念語ビューで accepted / plain-language / avoid が整理され、表記揺れや過剰な concept-term compression が残っていない。
- AI Writer の authoring intent、TODO、後で埋める内容、作業計画が公開本文 prose に残っていない。必要なものは `% INTENT:` / `% TODO-PAPER:`、`_paperops/notes/`、`_paperops/model/issues/` へ移っている。
- `% PREDICTED-RESULT:`、`% SIM-REQUEST:`、`% EXPECTATION-BASIS:`、`% REPLACE-XX:`、`xx` placeholder が投稿版に残っていない。予測稿を使った block は、対応する追加シミュレーション、result / figure card 更新、`scientific-gate` の再判定が閉じている。
- `check-predicted-results.py --root . --scope all --strict` と `make submission-gate` が通り、open AREQ、authoring source marker、submission drift が submission candidate に残っていない。
- 実査読改訂では、comment inventory、response matrix、本文変更、response letter が対応している。
- 最終 PDF / TeX / response letter のどれを成果物とするかを明示し、最終 commit または共有すべき artifact を記録している。

## Checks

完了前は `make finish-manuscript-check` を実行する。原稿を編集したら `make mirror-check`、引用や bibliography に触れたら `make citation-check`、概念語に触れたら `make concept-term-check`、AI 執筆意図を整理したら `make authoring-intent-check`、図表に触れたら `make figure-reference-check` と `make figure-obligation-check`、claim / evidence / layer card に触れたら `make claim-evidence-check` と `make paper-layer-card-check` を実行する。

storyline を更新したら `make storyline-check` と `make section-contract-check` を実行する。投稿前には `scripts/check-storyline.py --root . --strict`、`scripts/check-section-contracts.py --root . --strict`、`scripts/check-public-terms.py --root . --strict`、`scripts/check-figure-obligations.py --root . --strict`、`make submission-gate`、`make pre-submit` を使う。

AI が本文、レビュー、response draft に関与した場合は `ai-disclosure-check` を通す。文章を磨くために evidence の弱さを隠さない。`analysis-needed` や `assumption-blocked` は文体ではなく upstream route で処理する。予測稿が残る場合は `draft-predicted-results` の analysis request を閉じるまで完了扱いにしない。

raw confidential reviewer text を web 検索語、Issue、公開 PR、tracked notes に入れない。共有前に成果物、未解決 blocker、defer した hygiene、次の人間判断を短く列挙する。


## Typed mutation contract

六モデルの tracked document、index、revision、hash、dependency、approval、manifest、journal を直接編集しない。意味判断と candidate document の作成後、ignored な YAML/JSON change request に必要な upsert/delete をすべて明示し、`pops change plan <request.yml>`、`pops change diff <change-id>`、`pops change apply <change-id> --yes` に適用を委譲する。delete cascade は推測せず、dependent update/delete を同じ request に含める。raw review、credential、private/local path は request や tracked model に入れない。既存 legacy project を読む場合だけ migration reader を使い、通常 authoring では legacy card や macro-state file に fallback しない。
