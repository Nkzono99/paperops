from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

from paperops.build import parse_log
from paperops.cli import main

from .conftest import write

LOG = """\
This is XeTeX, Version 3.14159265
LaTeX Warning: Reference `fig:floor' on page 1 undefined on input line 12.
LaTeX Warning: Citation `smith2019' on page 2 undefined on input line 30.
LaTeX Warning: Citation `smith2019' on page 3 undefined on input line 44.
Package natbib Warning: Citation `a-very-long-citation-key-that-wraps' on page 3 undefined on i
nput line 50.
Overfull \\hbox (12.0pt too wide) in paragraph at lines 5--6
./sections/results.tex:14: Undefined control sequence.
! Emergency stop.
l.14 \\foo
Output written on ../build/main.pdf (3 pages).
"""


def test_parse_log_collects_problems() -> None:
    result = parse_log(LOG)
    assert result.undefined_refs == ["fig:floor"]
    assert result.undefined_cites == ["smith2019", "a-very-long-citation-key-that-wraps"]
    assert result.overfull == 1
    assert result.pages == 3
    assert result.errors == [
        "sections/results.tex:14: Undefined control sequence.",
        "Emergency stop. l.14 \\foo",
    ]


def test_build_reports_missing_engine(paper: Path, capsys) -> None:
    config = paper / "paper.toml"
    config.write_text(
        config.read_text("utf-8").replace('engine = "xelatex"', 'engine = "no-such-tex"'),
        encoding="utf-8",
    )
    assert main(["build"]) == 1
    assert "no-such-tex" in capsys.readouterr().err


needs_tex = pytest.mark.skipif(
    not (shutil.which("xelatex") and shutil.which("bibtex")), reason="needs xelatex and bibtex"
)


def english_paper(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "paper-en"
    assert main(["init", str(root), "--lang", "en", "--style", ""]) == 0
    monkeypatch.chdir(root)
    return root


@needs_tex
def test_fresh_project_builds(tmp_path: Path, monkeypatch, capsys) -> None:
    root = english_paper(tmp_path, monkeypatch)
    assert main(["build"]) == 0
    assert "built build/main.pdf (1 pages)" in capsys.readouterr().out
    assert (root / "build/main.pdf").is_file()
    assert not list((root / "manuscript").glob("*.aux"))


@needs_tex
def test_build_resolves_references_and_citations(tmp_path: Path, monkeypatch, capsys) -> None:
    root = english_paper(tmp_path, monkeypatch)
    write(
        root / "manuscript/refs.bib",
        "@article{smith2019, author={Smith, A.}, title={Holes}, journal={J. Test}, year={2019}}\n",
    )
    write(
        root / "manuscript/sections/results.tex",
        "\\section{Results}\\label{sec:r}\nSee Section~\\ref{sec:r} and \\citet{smith2019}.\n"
        "Missing \\ref{nope} and \\citep{ghost}.\n",
    )
    main_tex = root / "manuscript/main.tex"
    main_tex.write_text(
        main_tex.read_text("utf-8").replace(
            "\\end{document}",
            "\\input{sections/results}\n\\bibliographystyle{plainnat}\n\\bibliography{refs}\n"
            "\\end{document}",
        ),
        encoding="utf-8",
    )
    assert main(["build"]) == 0
    out = capsys.readouterr().out
    assert "undefined references: nope" in out
    assert "undefined citations: ghost" in out
    assert "sec:r" not in out and "smith2019" not in out

    assert main(["context"]) == 0
    out = capsys.readouterr().out
    assert "build/main.pdf" in out and "pops build" not in out
    later = time.time() + 60
    os.utime(root / "manuscript/sections/results.tex", (later, later))
    assert main(["context"]) == 0
    out = capsys.readouterr().out
    assert "(stale)" in out and "next: the PDF is older" in out


@needs_tex
def test_build_failure_points_to_the_line(tmp_path: Path, monkeypatch, capsys) -> None:
    root = english_paper(tmp_path, monkeypatch)
    main_tex = root / "manuscript/main.tex"
    main_tex.write_text(
        main_tex.read_text("utf-8").replace("\\maketitle", "\\maketitle\n\\undefinedmacro"),
        encoding="utf-8",
    )
    assert main(["build"]) == 1
    out = capsys.readouterr().out
    assert "build failed; full log: build/main.log" in out
    assert "main.tex:11: Undefined control sequence." in out
