"""The managed block of a paper project's ``AGENTS.md`` and skill deployment."""

from __future__ import annotations

import re
import shutil
from importlib import resources
from pathlib import Path

from paperops import __version__

BEGIN = "<!-- paperops:begin -->"
END = "<!-- paperops:end -->"
SKILL_ROOTS = (".agents/skills", ".claude/skills")
_VERSION_RE = re.compile(r"<!-- paperops-version: (\S+) -->")

BLOCK = """\
{begin}
<!-- paperops-version: {version} -->
# {title}

この repository は論文 1 本を書く paperops project です。agent が主張の設計から図・本文・PDF までを作り、
著者（人間）は BRIEF の承認と添削コメントで方向を決めます。著者とのやりとりは日本語で行います。

## ファイルの役割

| ファイル | 役割 |
|---|---|
| `BRIEF.md` | 何を言う論文か。主張 1 文、主要な発見、載せないもの、図の割り当て、段落骨子、未決（著者の判断が要る点）。本文はこれに従う |
| `STYLE.md` と共有 STYLE | 著者の文体・構成・図の好み。添削コメントから学んだ規則がここに溜まる |
| `manuscript/` | `main.tex`、`sections/`、`numbers.tex`（本文に出す数値と出典）、`refs.bib` |
| `figures/<name>/` | 図 1 枚につき 1 directory。`make.py`、`figure.md`（設計と推敲記録）、出力 |
| `paper.toml` | 参照する source（runops project など）、言語、build 設定、共有 STYLE の場所 |
| `LOG.md` | 決めたことと理由。日付見出しで追記する |

## Commands

| command | effect |
|---|---|
| `pops context [--json]` | 現状の一覧: BRIEF と発見の状態、STYLE、source と解析 topic、図、残っている予想、未対応の添削コメント、build |
| `pops outline [--json]` | 見出し、各段落の第 1 文と分量、caption の第 1 文。骨子の確認に使う |
| `pops build [--main PATH]` | PDF を `build/` に作り、エラー・未定義の参照と引用を要約する |
| `pops update` | この block と skill を、導入されている paperops の版に合わせる |

## 進め方

- **最初に `pops context` を読む。** BRIEF の状態、未対応コメント、図と build の鮮度がわかり、次にやることが決まります。
- **主張を先に決め、本文をそれに従わせる。** BRIEF.md の主張 1 文と主要な発見が、何を書き、何を削るかの基準です。
  BRIEF が `approved` のとき、主張・発見・載せないものを変える案は著者に確認してから反映します
  （段落骨子、図の割り当て、未決は、直して報告すれば足ります）。
  `draft` のときは案を見せて承認を得るか、「任せる」と言われたら推奨案で進めます。
- **主張文は言い切り、厳密さは置き場に書く。** 成立条件・例外・不確かさは、BRIEF で決めた置き場
  （Methods、該当する結果の直後、Discussion の限界の段落）に一度だけ書きます。置き場の節がまだ無ければ、
  その節を作って書きます。数値の定義と出典は `numbers.tex` が持ちます。置き場に書いてあるので、
  主張文を短く言い切っても正確さは失われません。
- **結果がまだ無い所は、予想で先に書く。** 論文全体の流れを、結果が揃う前に著者が見るためです。
  予想の結果・解釈・意味を完成形の文で書き、`\\pred{{}}` と状態（BRIEF の発見、`figure.md`）で予想と分かるようにし、
  そう考える理由を BRIEF に添えます。予想するのはこれから得る結果で、実行済みの run、手元の data、
  文献の内容は確かめたことを書きます。
- **主張を支える証拠が揃ったら、検証を足すより発表を優先する。** 計算資源と著者の時間は限られていて、
  論文は発表されて初めて使われます。手間は、結果次第で主張が覆る所に使います。
  外れたら驚くような予想は理由 1 行で進め、どちらに転ぶか分からず主張が変わる予想（賭け）にだけ、当たりの基準と
  外れた場合を書いて先に確かめます。確認済みの発見に上乗せする検証（収束、感度、条件の拡張）は、
  疑いが当たっていても驚かず、当たれば主張や発見が覆るものに絞ります。主張の範囲を変えるだけの疑いには
  計算を足さず、行った計算の範囲を成立条件として書きます。証拠が揃ったと言えるのは、主張の柱の発見が
  source 側の判定（定常、収束）を満たしたときです。発表するかどうかは著者が決めるので、BRIEF の
  「これから要る計算」には発表までに要るものだけを載せ、残っているものの一覧として保ちます。
- **主張を支える根拠を前に出し、限界は一度、具体的に書く。** 得られた結果から主張を補強するものを選んで
  本文と図の中心に置きます。主張の範囲を狭める事実は、限界の段落に隠さず書きます。
- **添削は `%>` と会話で受け、原稿全体と STYLE に広げる。** 著者は TeX に `%> コメント` を書くか、会話で伝えます。
  段落の上の `%>` はその段落全体に、行末の `%>` はその文に付いたものとして読みます。
  指摘箇所を直したら、同じ好みが当てはまる他の箇所も直し、好みを STYLE に規則として残します。
  対応した `%>` 行は消し、判断が要るものは残して理由を伝えます。
- **図は、描く前に設計し、描画結果を見て推敲してから見せる。** 図 1 枚は、読者に 1 つの比較をさせて
  1 つのメッセージを渡します。描く前に `figure.md` へメッセージと載せないものを決め、掲載寸法の画像を自分で見て、
  設計を知らない読者がメッセージを読めるまで直します。
- **source は読む場所として使う。** `paper.toml` の `[[sources]]` が指す project の `LOG.md`、`notes/`、
  解析の `README.md` と `out/` の小さな縮約出力、`cases/`、run の `manifest.toml` から結果と根拠を読みます。図の script と縮約データは
  この repository の `figures/` に置きます。source 側で run や解析を足す必要が出たら、必要な内容を
  著者に伝えます（その project の session が実行します）。
- **数値と文献には出典を付ける。** 本文の数値は `numbers.tex` のマクロで書き、出典（source 名、run id、
  解析の path）をコメントに残します。文献は実在を確認できたものを `refs.bib` に入れ、未確認の箇所は
  `\\note{{要出典: ...}}` で PDF に見える形にします。
- **決定は `LOG.md` に、著者の判断が要る点は `BRIEF.md` の未決に書く。** 未決は `pops context` に出るので、
  次の session と著者の目に入ります。解決したら未決から消し、決定を `LOG.md` に移します。
- **英語版は依頼されたら作る。** `manuscript/en/` に `main.tex` と `sections/` を置き、`numbers.tex`、
  `refs.bib`、`figures/` は共有します（`pops build --main manuscript/en/main.tex`）。

## Skills

| skill | 使う場面 |
|---|---|
| `paper-brief` | 主張 1 文、主要な発見、載せないもの、段落骨子を決める。書き始める前と、主張や構成への指摘を受けたとき |
| `paper-draft` | BRIEF から図・数値・本文・PDF までを通して作る |
| `paper-figure` | 図を作る、推敲する、図への指摘を反映する |
| `paper-revise` | 添削コメントを反映し、同種の箇所へ広げ、好みを STYLE に学習する |
| `paper-predict` | まだ無い結果を予想で先に書く、これから要る計算を並べる、結果が出たら答え合わせをする |
| `paper-check` | 読者テスト（何を言う論文かが伝わるか）と、数値・引用・予想の印・build の照合 |
{end}
"""


def render_block(title: str) -> str:
    return BLOCK.format(begin=BEGIN, end=END, version=__version__, title=title or "paper")


def write_harness(root: Path, title: str) -> list[str]:
    """Create or refresh the managed block; text outside the markers is the project's own."""
    written = []
    block = render_block(title)
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        if BEGIN in text and END in text:
            head, _, rest = text.partition(BEGIN)
            _, _, tail = rest.partition(END)
            text = head + block.rstrip("\n") + tail
        else:
            text = block + "\n" + text
    else:
        text = block
    agents.write_text(text, encoding="utf-8")
    written.append("AGENTS.md")
    claude = root / "CLAUDE.md"
    if not claude.exists():
        claude.write_text("@AGENTS.md\n", encoding="utf-8")
        written.append("CLAUDE.md")
    return written


def deployed_version(root: Path) -> str:
    try:
        match = _VERSION_RE.search((root / "AGENTS.md").read_text(encoding="utf-8"))
    except OSError:
        return ""
    return match.group(1) if match else ""


def skill_source() -> Path:
    return Path(str(resources.files("paperops") / "skills"))


def deploy_skills(root: Path) -> list[str]:
    """Copy the packaged skills into both agent skill roots, replacing earlier copies."""
    names = []
    for src in sorted(p for p in skill_source().iterdir() if (p / "SKILL.md").is_file()):
        names.append(src.name)
        for skill_root in SKILL_ROOTS:
            dest = root / skill_root / src.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
    return names
