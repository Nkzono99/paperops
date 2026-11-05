# paperops

paperops は、AI エージェントと論文を 1 本書くための最小限のハーネスです。エージェントが主張の設計から
図・本文・PDF までを作り、著者は主張の承認と添削コメントで方向を決めます。添削から読み取った著者の好みは
STYLE に溜まり、次の草稿と次の論文に効きます。人が打つコマンドは `pops init` だけです。

## 流れ

```text
結果（runops project など）
   │  paper-brief   主張 1 文の候補 → 著者が選ぶ → 発見・載せないもの・段落骨子
   ▼
BRIEF.md ──► paper-figure  図を描き、描画結果を見て推敲
   │         paper-draft   数値・本文・PDF を通して作る
   │         paper-check   初見の読者に読ませ、受け取った主張を BRIEF と比べる
   ▼
PDF ──► 著者が `%>` で添削 ──► paper-revise  反映 → 同種の箇所へ広げる → STYLE に学習
```

## はじめる

```bash
uv tool install paper-harness-cli
pops init paper-my-topic --source ~/large1/project_cylindrical_hole
cd paper-my-topic
```

できた directory で Codex か Claude Code を起動して、書きたい論文について話しかけてください。
`--source` は結果の出どころ（runops project の root など）で、複数指定でき、後から `paper.toml` に足せます。
英語で書き始めるときは `--lang en` を付けます。

## 頼めること

| やりたいこと | 頼み方の例 |
|---|---|
| 主張を決める | project_cylindrical_hole の結果で論文を書きたい。主張の候補を出して |
| 通して書かせる | 案 A で進めて。図と本文を最後まで作って PDF を見せて |
| 骨子を見る | 各段落の第 1 文だけ並べて見せて |
| 図を直す | 図 2 は主役の線が埋もれている。直して、他の図も同じ基準で見直して |
| 添削を反映する | `%>` でコメントを入れた。反映して、好みは STYLE に残して |
| 伝わるか確かめる | 初見の読者に読ませて、何を言う論文に見えるか確かめて |
| 英語版を作る | 日本語稿が固まったので英語版を作って |
| 更新する | paperops を最新にして（`pops update`） |

添削は、TeX に `%>` で始まるコメントを書くだけです。段落の上に書くとその段落全体に、行末に書くとその文に付きます。

```tex
%> 結論を先に。条件は Methods に回す
本研究で用いた条件の範囲において、空洞底部の電位は……
```

## project の中身

```text
paper-my-topic/
├── paper.toml            source、言語、build、共有 STYLE の場所
├── BRIEF.md              何を言う論文か: 主張 1 文、発見、載せないもの、図の割り当て、段落骨子
├── STYLE.md              この論文での書き方。添削から学んだ規則
├── manuscript/
│   ├── main.tex, preamble.tex, sections/
│   ├── numbers.tex       本文に出す数値のマクロと出典
│   └── refs.bib
├── figures/
│   ├── paper.mplstyle, common.py
│   └── <name>/           make.py, figure.md（メッセージと推敲記録）, data/, <name>.pdf, <name>.png
├── LOG.md                決めたことと理由
├── build/                PDF（Git の対象外）
└── AGENTS.md, .agents/skills/, .claude/skills/
```

論文をまたいで使う著者の好みは `~/.config/paperops/STYLE.md` に置かれます（`pops init --style FILE` で変更）。

## 設計の要点

- **主張を先に決める。** エージェントに任せると、結果を正確に並べた、何を言いたいのかわからない原稿に
  なりがちです。`BRIEF.md` に主張 1 文と「載せないもの」を先に決め、本文をそれに従わせます。
- **言い切りと厳密さを分ける。** 成立条件は BRIEF で決めた置き場に一度だけ書き、数値の出典は
  `numbers.tex` が持ちます。厳密さの置き場があるので、主張の文は短く言い切れます。
- **伝わったかは初見の読者で測る。** 主張を知らない別のエージェントに PDF だけを読ませ、受け取った
  主張 1 文を BRIEF と比べます。
- **図は見て直す。** 掲載寸法の描画結果を見て直す round を回し、記録を `figure.md` に残します。
- **数個の添削を全体に効かせる。** 指摘を規則にして原稿全体へ広げ、STYLE に残します。

## コマンド

エージェントが使います。人が覚える必要はありません。

| command | effect |
|---|---|
| `pops init [DIR] [--source DIR]... [--lang ja\|en] [--title T] [--style FILE]` | 論文 project を作る |
| `pops context [--json]` | 現状: BRIEF、STYLE、source と解析 topic、図、未対応コメント、build |
| `pops outline [--json]` | 見出し、各段落の第 1 文と分量、caption の第 1 文 |
| `pops build [--main PATH]` | PDF を作り、エラー・未定義の参照と引用を要約 |
| `pops update` | `AGENTS.md` の管理 block と skill を更新 |

## 1.x からの移行

2.0 は作り直しで、1.x の typed model（`_paperops/`）、`pops change` / `compile` / `workflow` などは
ありません。1.x の project は `paper-harness-cli==1.0.0` のまま使い続けられます。2.0 へ移すときは、
新しい directory で `pops init` し、原稿の TeX と図を `manuscript/` と `figures/` に移してから、
エージェントに既存の原稿から `BRIEF.md` を起こすよう頼んでください。

---

[SPEC](SPEC.md) · [開発に参加する](AGENTS.md)
