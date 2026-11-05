# paperops SPEC

paperops 2 の設計上の約束。実装と skill を変えるときは、ここと食い違わないようにする。

## 1. 目的

AI エージェントが論文 1 本を主張の設計から PDF まで作り、著者は主張の承認と数個の添削コメントで
方向を決める。そのために必要な最小限だけを提供する。

- 書く前に「何を言う論文か」を決め、本文をそれに従わせる。
- 図を、描画結果を見て推敲する。
- 添削コメントを原稿全体に広げ、著者の好みを規則として蓄える。
- runops project などの source から結果と根拠を読む。
- 結果がまだ無い所を、根拠のある予想で先に書き、あとから答え合わせをする。

やらないこと（実際の執筆で必要になったら、その時に足す）:
型付きの中間モデルと検証、変更の transaction と rollback、1.x project の自動移行、日英 block の同期管理、
査読対応、投稿用 package の生成、論文 repository 用の CI、LLM API の呼び出し。

## 2. 原則

1. **状態は読めるファイルに置く。** `BRIEF.md`、`STYLE.md`、`figure.md`、`numbers.tex`、`LOG.md`、原稿の TeX が
   全てで、CLI は隠れた状態を持たない。どの session から入っても同じ状態が読める。
2. **CLI は決定的な作業だけを担う。** 雛形の展開、現状の一覧、骨子の抽出、build と log の要約。
   意味の判断（主張、取捨、文章、図の良し悪し）は skill に書く。
3. **予算を守る。** コマンドは 6 個まで、skill は 6 個まで、実行時の依存は標準 library のみ。
   増やす前に、既存のものへ吸収できないかを確かめる。
4. **著者の手間は 3 か所に集める。** BRIEF の承認、図の確認、草稿への添削。それ以外は自動で進める。
5. **ハーネスの文章は「何をするか」と理由で書く。** 禁止の列挙にしない。方針は `AGENTS.md` の block に 1 か所、
   手順は skill に書き、同じことを 2 か所に書かない。
6. **管理するものと project のものを分ける。** `pops update` が書き換えるのは `AGENTS.md` の管理 block と
   `paper-*` skill だけ。それ以外は project のもので、`pops init` も既存のファイルを上書きしない。

## 3. project の構成

| path | 持ち主 | 内容 |
|---|---|---|
| `paper.toml` | project | `[paper] title, lang, main`、`[build] engine, bib, tex_bin`、`[style] shared`、`[[sources]] name, path, note` |
| `BRIEF.md` | project | 状態、主張 1 文、問いと意義、主要な発見（発見ごとに状態・根拠・成立条件と置き場、予想なら確かめ方・外れたら）、載せないもの、図の割り当て、段落骨子、検証の順番、未決 |
| `STYLE.md` | project | この論文の規則。節: 文章、構成、図、用語と表記、候補、共有待ち |
| 共有 STYLE（既定 `~/.config/paperops/STYLE.md`） | 著者 | 論文をまたぐ規則。`pops init` が無ければ作る |
| `manuscript/` | project | `main.tex`、`preamble.tex`、`sections/`、`numbers.tex`、`refs.bib`。英語版は `manuscript/en/` |
| `figures/<name>/` | project | `make.py`、`figure.md`、`data/`、`<name>.pdf`、`<name>.png` |
| `figures/common.py`、`figures/paper.mplstyle` | project | 図の共通 helper と見た目 |
| `LOG.md` | project | 決めたことと理由。著者の判断が要る点は `BRIEF.md` の未決に置き、`pops context` に出す |
| `build/` | 生成物 | PDF と LaTeX の中間ファイル。Git の対象外 |
| `AGENTS.md` の `<!-- paperops:begin -->`〜`<!-- paperops:end -->` | paperops | 方針、コマンド、skill の一覧。版を `<!-- paperops-version: X -->` に持つ |
| `.agents/skills/paper-*`、`.claude/skills/paper-*` | paperops | skill の複製 |

## 4. CLI が読む書式

`pops context` と `pops outline` は次の書式だけに依存する。skill と雛形はこれを保つ。

- `BRIEF.md`、`figure.md`: 行頭の `状態: <語>`。BRIEF は `draft` / `approved`、図は `draft` / `reviewed` / `approved` / `predicted`。
- `BRIEF.md`: `## 主張` で始まる見出しの下の最初の行が主張 1 文。`## 未決` の下の `- ` 行が未決。
  `## 主要な発見` の下の `### <id> ...` が発見 1 個で、続く `- 状態: <語>`（`確認済み` / `予想` / `一部確認`）がその状態。
- `STYLE.md`: `## 候補` と `## 共有待ち` 以外の節の、行頭の `- ` が規則 1 個。字下げした行（例、由来）は数えない。
- `figure.md`: `## メッセージ` で始まる見出しの下の最初の行が図のメッセージ。行頭の `- R<数字>` が推敲 1 round。
- 原稿: `%>` で始まる TeX コメントが未対応の添削。連続する `%>` 行は 1 個にまとめ、続く段落に付く
  （一覧にはその最初の行を出す）。行末の `%>` はその文に付く。
- 原稿: `\pred{` が、まだ得ていない結果の印 1 個（TeX コメントの中は数えない）。
- 原稿: 段落は空行で区切る。`\input` は main のある directory から解決する。
- Markdown の `<!-- ... -->` は説明として読み飛ばす。

## 5. コマンド

| command | 動作 |
|---|---|
| `pops init [DIR]` | 雛形を展開（既存ファイルは残す）、共有 STYLE を用意、管理 block と skill を配置、Git repository が無ければ作る |
| `pops update` | 管理 block と skill を導入中の版に合わせる |
| `pops context [--json]` | BRIEF と発見の状態、STYLE、source（runops project なら解析 topic の README）、原稿、build、図、残っている `\pred`、未対応コメント、次の一手 |
| `pops outline [--main PATH] [--json]` | 見出し、段落の第 1 文と分量、float の caption 第 1 文と label |
| `pops build [--main PATH]` | engine → 必要なら bibtex / biber → engine を収束まで。`build/` に出力し、log を要約。失敗は終了 code 1 |

source の解析 topic は、`analysis/*/README.md` と、`runs/` の下の `_analysis/*/README.md` を探す。
run directory（`manifest.toml` を持つ）と `_` で始まる directory の中は探さない。

## 6. skill

| skill | 入力 | 出力 |
|---|---|---|
| `paper-brief` | source、著者の狙い | `BRIEF.md`（著者の承認） |
| `paper-draft` | `BRIEF.md`、STYLE | 図、`numbers.tex`、`sections/`、PDF、著者への引き渡し |
| `paper-figure` | 図のメッセージ、source の data | `figures/<name>/`、推敲記録 |
| `paper-revise` | `%>` コメント、会話の指摘 | 直した原稿、STYLE の規則、報告 |
| `paper-predict` | 主張に必要でまだ無い結果、source の case と過去の run | 予想の発見（根拠・確かめ方・外れたら）、検証の順番、答え合わせの結果 |
| `paper-check` | PDF、`BRIEF.md` | 読者が受け取った主張と BRIEF の差、照合の結果 |

## 7. 主張が伝わるようにする仕組み

エージェントは結果を正確に、同じ重みで、留保を付けて書く傾向があり、そのままでは何を言う論文かが見えない。
次の 4 つで制御する。

1. **選択を先に固定する。** `BRIEF.md` に主張 1 文と「載せないもの」を書き、著者が承認する。
2. **厳密さに置き場を与える。** 発見ごとに「言い切り文」と「成立条件と置き場」を対で持ち、数値の定義と出典は
   `numbers.tex` に置く。主張の文から留保を外しても情報は失われない。
3. **骨子で確かめる。** `pops outline` が段落の第 1 文と分量を並べ、BRIEF の段落骨子と比べられる。
4. **初見の読者で測る。** 主張を知らない別のエージェントに PDF だけを読ませ、受け取った主張 1 文を BRIEF と比べる。

## 8. 好みを学ぶ仕組み

1. 著者が `%>` か会話で添削する。
2. `paper-revise` が指摘箇所を直し、好みを「行動 + 例（前 → 後）+ 由来」の規則にする。
3. 規則は、どの論文にも当てはまるなら共有 STYLE、この論文だけなら `STYLE.md` に置く。
   一般性が不確かなものは `STYLE.md` の「候補」に置き、2 回目の観測で規則へ昇格する。
4. 規則になったものは原稿全体へ広げ、どこを変えたかを著者に報告する。著者は規則を直せる。
5. 図の見た目の設定は `paper.mplstyle` に入れ、全ての図に決定的に効かせる。
6. `paper-draft` と `paper-figure` は、書く前に両方の STYLE を読む。

## 9. 予想で先に書く仕組み

エージェントは、手元の結果で言えることだけで原稿を閉じる傾向がある。それでは、結果が揃う前に論文全体の流れを
確かめ、必要な計算を決める、という進め方ができない。予想を許し、作り話と区別できる形を与える。

1. **予想の 4 条件。** 印（`\pred{}`、発見と図の状態）、根拠、確かめ方、外れた場合。4 つが揃えば予想として書ける。
2. **予想の対象を限る。** 予想するのはこれから得る結果だけ。実行済みの run、手元の data、文献の内容は確かめたことを書く。
3. **完成形で書く。** 予想の結果・解釈・意味を、結果が出たときの文で書く。印は文体ではなく `\pred{}` が担う。
4. **得られるかを見積もる。** source の case、simulator の文書、過去の run の資源から、いまの simulator で出せるか、
   費用はどれほどかを書く。分からないことは分からないと書く。
5. **賭けている所を見せる。** 主張が予想に依っているときは、どの部分が予想かと、外れても言える主張を主張 1 文の下に書く。
   予想は代表値と幅で書き、当たりの基準は外れた場合と区別できる線に置く。
6. **根拠を残す。** 数値の予想は `numbers.tex` のコメントに、図の予想は `make.py` の `predict()` に code として書く。
7. **答え合わせをする。** 当たりの基準は結果を見る前に BRIEF に書く。当たれば印を外し、外れたら文章をぼかさずに
   主張と発見を直す。投稿前には印が 0 個であることを `pops context` で確かめる。
