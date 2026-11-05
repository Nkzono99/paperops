# 論文 project

[paperops](https://github.com/Nkzono99/paperops) で作った論文 1 本分の repository です。
この directory で Codex か Claude Code を起動して、書きたい論文について話しかけてください。

## 頼み方の例

| やりたいこと | 頼み方の例 |
|---|---|
| 主張を決める | project_cylindrical_hole の結果で論文を書きたい。主張の候補を出して |
| 通して書かせる | BRIEF の案 A で進めて。図と本文を最後まで作って PDF を見せて |
| 骨子を見る | 各段落の第 1 文だけ並べて見せて |
| 図を直す | 図 2 は主役の線が埋もれている。直して、他の図も同じ基準で見直して |
| 添削を反映する | `%>` でコメントを入れた。反映して、好みは STYLE に残して |
| 伝わるか確かめる | 初見の読者に読ませて、何を言う論文に見えるか確かめて |
| 英語版を作る | 日本語稿が固まったので英語版を作って |

## 添削の入れ方

TeX に `%>` で始まるコメントを書きます。段落の上に書くとその段落全体に、行末に書くとその文に付きます。
会話で伝えても同じです。

```tex
%> 結論を先に。条件は Methods に回す
本研究で用いた条件の範囲において、空洞底部の電位は……
```

## 中身

```text
BRIEF.md          何を言う論文か（主張 1 文、発見、載せないもの、段落骨子）
STYLE.md          この論文での書き方。添削から学んだ規則
manuscript/       main.tex, sections/, numbers.tex, refs.bib
figures/<name>/   make.py, figure.md, 出力
paper.toml        source、言語、build の設定
LOG.md            決めたことと理由
build/            PDF（Git の対象外）
```
