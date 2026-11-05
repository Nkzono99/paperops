from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from paperops import __version__
from paperops.cli import main
from paperops.harness import BEGIN, END, SKILL_ROOTS
from paperops.project import load_project

from .conftest import write

SKILLS = ["paper-brief", "paper-check", "paper-draft", "paper-figure", "paper-revise"]


def test_init_creates_project_and_harness(paper: Path, tmp_path: Path) -> None:
    for rel in (
        "paper.toml",
        "BRIEF.md",
        "STYLE.md",
        "LOG.md",
        ".gitignore",
        "manuscript/main.tex",
        "manuscript/preamble.tex",
        "manuscript/numbers.tex",
        "manuscript/refs.bib",
        "figures/common.py",
        "figures/paper.mplstyle",
        "figures/_template/make.py",
        "AGENTS.md",
        "CLAUDE.md",
    ):
        assert (paper / rel).is_file(), rel
    assert not (paper / "manuscript/preamble.ja.tex").exists()
    assert not (paper / "gitignore").exists()
    assert "XeTeXlinebreaklocale" in (paper / "manuscript/preamble.tex").read_text("utf-8")
    assert (tmp_path / "shared" / "STYLE.md").is_file()
    for root in SKILL_ROOTS:
        assert sorted(p.name for p in (paper / root).iterdir()) == SKILLS
        for name in SKILLS:
            text = (paper / root / name / "SKILL.md").read_text("utf-8")
            assert text.startswith(f"---\nname: {name}\ndescription: ")

    project = load_project(paper)
    assert project.title == "paper-test"
    assert project.lang == "ja"
    assert project.shared_style == tmp_path / "shared" / "STYLE.md"
    assert f"paperops-version: {__version__}" in (paper / "AGENTS.md").read_text("utf-8")


def test_init_records_sources_and_language(tmp_path: Path) -> None:
    first = tmp_path / "project_hole"
    second = tmp_path / "other" / "project_hole"
    first.mkdir()
    second.mkdir(parents=True)
    root = tmp_path / "paper"
    args = ["init", str(root), "--lang", "en", "--title", 'A "quoted" title', "--style", ""]
    assert main([*args, "--source", str(first), "--source", str(second)]) == 0

    config = tomllib.loads((root / "paper.toml").read_text("utf-8"))
    assert config["paper"] == {
        "title": 'A "quoted" title',
        "lang": "en",
        "main": "manuscript/main.tex",
    }
    assert [s["name"] for s in config["sources"]] == ["hole", "hole-2"]
    assert config["sources"][0]["path"] == str(first)
    assert "fontspec" not in (root / "manuscript/preamble.tex").read_text("utf-8")
    assert load_project(root).shared_style is None


def test_init_keeps_existing_files_and_refuses_twice(tmp_path: Path, capsys) -> None:
    root = tmp_path / "paper"
    write(root / "manuscript/main.tex", "my own manuscript\n")
    write(root / "AGENTS.md", "# my rules\n")
    assert main(["init", str(root), "--style", ""]) == 0
    assert (root / "manuscript/main.tex").read_text("utf-8") == "my own manuscript\n"
    agents = (root / "AGENTS.md").read_text("utf-8")
    assert agents.startswith(BEGIN) and agents.rstrip().endswith("# my rules")

    assert main(["init", str(root), "--style", ""]) == 1
    assert "already a paperops project" in capsys.readouterr().err


def test_init_rejects_missing_source(tmp_path: Path, capsys) -> None:
    assert main(["init", str(tmp_path / "p"), "--source", str(tmp_path / "nope")]) == 1
    assert "not a directory" in capsys.readouterr().err
    assert not (tmp_path / "p").exists()


def test_update_refreshes_harness_and_keeps_project_files(paper: Path) -> None:
    write(paper / "BRIEF.md", "# mine\n")
    agents = paper / "AGENTS.md"
    text = agents.read_text("utf-8")
    edited = text.replace(f"paperops-version: {__version__}", "paperops-version: 0.0.1")
    agents.write_text("intro\n\n" + edited + "\n## my section\n", encoding="utf-8")
    skill = paper / ".claude/skills/paper-draft/SKILL.md"
    skill.write_text("stale", encoding="utf-8")
    write(paper / ".claude/skills/my-own/SKILL.md", "kept")

    assert main(["update"]) == 0
    text = agents.read_text("utf-8")
    assert text.startswith("intro\n\n" + BEGIN)
    assert text.rstrip().endswith("## my section")
    assert text.count(BEGIN) == 1 and text.count(END) == 1
    assert f"paperops-version: {__version__}" in text
    assert skill.read_text("utf-8").startswith("---\nname: paper-draft")
    assert (paper / ".claude/skills/my-own/SKILL.md").read_text("utf-8") == "kept"
    assert (paper / "BRIEF.md").read_text("utf-8") == "# mine\n"


def test_commands_outside_a_project_explain(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["context"]) == 1
    assert "pops init" in capsys.readouterr().err


def test_context_reads_project_state(paper: Path, tmp_path: Path, capsys) -> None:
    source = tmp_path / "project_hole"
    write(source / "runops.toml", "")
    write(source / "LOG.md", "# log\n")
    write(source / "analysis/potential/README.md", "q")
    write(source / "runs/flat/scan/_analysis/speed/README.md", "q")
    write(source / "runs/flat/scan/R1--a/manifest.toml", "")
    write(source / "runs/flat/scan/R1--a/_analysis/hidden/README.md", "q")
    write(source / "runs/_archive/old/_analysis/gone/README.md", "q")
    config = paper / "paper.toml"
    config.write_text(
        config.read_text("utf-8")
        + f'\n[[sources]]\nname = "hole"\npath = "{source}"\n'
        + '\n[[sources]]\nname = "lost"\npath = "/nonexistent/dir"\n',
        encoding="utf-8",
    )
    write(
        paper / "BRIEF.md",
        "# BRIEF\n\n状態: approved\n<!-- 状態: draft -->\n\n## 主張（1文）\n\n<!-- hint -->\n"
        "深い空洞の底は低く帯電する。\n\n## 未決\n\n- 太陽風条件を増やすか\n- \n",
    )
    write(
        paper / "STYLE.md",
        "## 文章\n\n- 結論を先に書く。\n  - 例: a → b\n- 言い切る。\n\n## 候補\n\n- 体言止めを避ける。\n"
        "\n## 共有待ち\n\n<!-- - not counted -->\n",
    )
    write(
        paper / "manuscript/sections/results.tex",
        "\\section{結果}\n%> 結論を先に\n%> 条件は Methods へ\n本研究の条件では電位が下がる。\n\n"
        "空洞は深い。 %> これは要らない\n% ordinary comment\n50\\% の差がある。\n",
    )
    main_tex = paper / "manuscript/main.tex"
    main_tex.write_text(
        main_tex.read_text("utf-8").replace(
            "\\end{document}", "\\input{sections/results}\n\\end{document}"
        ),
        encoding="utf-8",
    )
    write(paper / "figures/floor/make.py", "")
    write(
        paper / "figures/floor/figure.md",
        "状態: reviewed\n\n## メッセージ（1文）\n\n<!-- hint -->\n底は低く帯電する。\n\n"
        "## 推敲記録\n\n- R1: a → b\n- R2: c → d\n",
    )
    write(paper / "figures/bare/make.py", "")
    write(paper / "figures/floor/floor.pdf", "")

    assert main(["context", "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["brief"] == {
        "exists": True,
        "status": "approved",
        "message": "深い空洞の底は低く帯電する。",
        "open_items": 1,
    }
    assert state["style"]["project"]["rules"] == 2
    assert state["style"]["project"]["candidates"] == 1
    assert state["style"]["project"]["pending"] == 0
    assert state["style"]["shared"]["exists"] is True

    hole, lost = state["sources"]
    assert hole["runops"] is True and hole["log_updated"]
    assert hole["analysis"] == [
        "analysis/potential/README.md",
        "runs/flat/scan/_analysis/speed/README.md",
    ]
    assert lost["exists"] is False

    assert state["manuscript"]["paragraphs"] == 2
    assert state["figures"] == [
        {"name": "bare", "status": "draft", "message": "", "rounds": 0, "output": "missing"},
        {
            "name": "floor",
            "status": "reviewed",
            "message": "底は低く帯電する。",
            "rounds": 2,
            "output": "ok",
        },
    ]
    assert state["comments"] == [
        {
            "file": "manuscript/sections/results.tex",
            "line": 2,
            "text": "結論を先に 条件は Methods へ",
            "target": "本研究の条件では電位が下がる。",
        },
        {
            "file": "manuscript/sections/results.tex",
            "line": 6,
            "text": "これは要らない",
            "target": "空洞は深い。",
        },
    ]
    assert any("2 open review comments" in hint for hint in state["next"])

    assert main(["context"]) == 0
    text = capsys.readouterr().out
    assert "brief: approved  message: 深い空洞の底は低く帯電する。" in text
    assert "runs/flat/scan/_analysis/speed/README.md" in text
    assert "manuscript/sections/results.tex:2: 結論を先に 条件は Methods へ" in text
    assert "  - bare: (no message in figure.md)" in text
    assert "  - floor: 底は低く帯電する。" in text


def test_context_on_fresh_project_points_to_brief(paper: Path, capsys) -> None:
    assert main(["context"]) == 0
    text = capsys.readouterr().out
    assert "message: (not written)" in text
    assert "paper-brief" in text
    assert "comments: none open" in text


def test_context_warns_when_harness_is_older(paper: Path, capsys) -> None:
    agents = paper / "AGENTS.md"
    agents.write_text(agents.read_text("utf-8").replace(__version__, "1.9.9"), encoding="utf-8")
    assert main(["context"]) == 0
    assert "pops update" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["[paper\n", '[[sources]]\nname = "x"\n'])
def test_broken_config_is_reported(paper: Path, capsys, bad: str) -> None:
    (paper / "paper.toml").write_text(bad, encoding="utf-8")
    assert main(["context"]) == 1
    assert "paper.toml" in capsys.readouterr().err
