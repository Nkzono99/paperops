# 外部ソース到達メモ

外部 Web、GitHub、論文ページ、動画、RSS、SNS、議論サイトなどを調べる前に、到達経路、認証、raw 保存先、refs への昇格方針を決めるためのメモ。

## Reach objective

- 調査目的: 未記入
- 原稿・claim との関係: 未記入
- public な検索語だけで足りるか: 未記入
- confidential / private 情報を含むか: 未記入

## Channel routing table

| source ID | channel | source / query | preferred route | fallback route | credential need | raw capture policy | promotion target | verification status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SR-0001 | paper-metadata / github / web-page / video-transcript / rss-news / social-discussion / local-link | 未記入 | 未記入 | 未記入 | none / local-cookie / token / human-only | no-raw / ignored-raw / curated-only | `notes/related-work-map.md` / `refs/summaries/` / `notes/reproducibility.md` / `notes/scientific-gate.md` | unsearched / found-unread / metadata-checked / read / cross-checked / not-usable |

## Doctor / availability result

`agent-reach` が利用可能な場合だけ、`agent-reach doctor --json` の要約をここに残す。利用できない場合は、Codex の web / GitHub CLI / ローカル clone など現在使える経路を書く。

- 未記入

## Curated findings

raw output ではなく、人間または AI が確認して論文へ使える形に整理した finding だけを書く。

| finding ID | source ID | 要約 | 使い道 | confidence | citation / URL |
| --- | --- | --- | --- | --- | --- |
| SF-0001 | SR-0001 | 未記入 | related work / method / reviewer risk / reproducibility / background-only | low / medium / high | 未記入 |

## Promotion queue

| finding ID | 昇格先 | 必要な確認 | status |
| --- | --- | --- | --- |
| SF-0001 | `refs/summaries/` / `.bib` / `notes/related-work-map.md` / `notes/scientific-gate.md` | 未記入 | open |

## Privacy / credential risks

- cookie、token、private URL、個人環境の絶対パス:
- 外部検索語にしてはいけない情報:
- tracked file に残さない raw artifact:
