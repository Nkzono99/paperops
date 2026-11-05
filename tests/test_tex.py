from __future__ import annotations

from pathlib import Path

from paperops.cli import main
from paperops.tex import first_sentence, outline, split_comment

from .conftest import write

MAIN = r"""\documentclass{article}
\title{Ignored. Before the document.}
\begin{document}
\maketitle
\begin{abstract}
\input{sections/abstract}
\end{abstract}
\input{sections/results}
\bibliography{refs}
\end{document}
ignored after the end
"""

ABSTRACT = "深い空洞の底は低く帯電する。壁が電子を\n遮るためである。\n"

RESULTS = r"""\section{結果}
\label{sec:results}
% a comment line inside nothing

深い空洞の底は、平坦面より \phiFloorDrop~V 低く帯電する（図\ref{fig:floor}）。
% a comment line does not end the paragraph
壁が電子を遮るためである。
\begin{equation}
  \phi = 1.5 。
\end{equation}
この差は深さが直径を超えると現れる。

\begin{figure}
  \centering
  \includegraphics{floor/floor}
  \caption{深い空洞の底は低く帯電する。線は深さ/直径の比 \textbf{0.5 {\it and} 2}。}
  \label{fig:floor}
\end{figure}

\subsection{Depth dependence}
The drop grows with depth, as shown in Fig. 3 and by Smith et al. (2019) for 0.5 V. It saturates.
"""


def project(tmp_path: Path) -> Path:
    write(tmp_path / "manuscript/main.tex", MAIN)
    write(tmp_path / "manuscript/sections/abstract.tex", ABSTRACT)
    write(tmp_path / "manuscript/sections/results.tex", RESULTS)
    return tmp_path


def test_split_comment_respects_escapes() -> None:
    assert split_comment("50\\% of it % note") == ("50\\% of it ", " note")
    assert split_comment("line break \\\\% note") == ("line break \\\\", " note")
    assert split_comment("no comment") == ("no comment", None)


def test_first_sentence() -> None:
    assert first_sentence("電位が下がる。壁が遮る。") == "電位が下がる。"
    assert first_sentence("See Fig. 2 for 1.5 V. Next one.") == "See Fig. 2 for 1.5 V."
    assert first_sentence("No terminator") == "No terminator"


def test_outline_lists_headings_first_sentences_and_captions(tmp_path: Path) -> None:
    root = project(tmp_path)
    items = outline(root / "manuscript/main.tex", root)
    summary = [(i.kind, i.text) for i in items]
    assert summary == [
        ("heading", "Abstract"),
        ("paragraph", "深い空洞の底は低く帯電する。"),
        ("heading", "結果"),
        (
            "paragraph",
            "深い空洞の底は、平坦面より \\phiFloorDrop~V 低く帯電する（図\\ref{fig:floor}）。",
        ),
        ("float", "深い空洞の底は低く帯電する。"),
        ("heading", "Depth dependence"),
        (
            "paragraph",
            "The drop grows with depth, as shown in Fig. 3 and by Smith et al. (2019) for 0.5 V.",
        ),
    ]
    abstract, results = items[1], items[3]
    assert abstract.size == "27字"
    assert (abstract.file, abstract.line) == ("manuscript/sections/abstract.tex", 1)
    assert (results.file, results.line) == ("manuscript/sections/results.tex", 5)
    assert items[4].label == "fig:floor"
    assert items[5].level == 2
    assert items[6].size == "21 words"


def test_outline_command(paper: Path, capsys) -> None:
    write(paper / "manuscript/main.tex", MAIN)
    write(paper / "manuscript/sections/abstract.tex", ABSTRACT)
    write(paper / "manuscript/sections/results.tex", RESULTS)
    assert main(["outline"]) == 0
    text = capsys.readouterr().out
    assert "# 結果" in text
    assert "  ## Depth dependence" in text
    assert "[float fig:floor] 深い空洞の底は低く帯電する。" in text
    assert "(27字; manuscript/sections/abstract.tex:1)" in text

    assert main(["outline", "--main", "manuscript/none.tex"]) == 1
    assert "main file not found" in capsys.readouterr().err
