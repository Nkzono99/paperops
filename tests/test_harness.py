"""The shipped harness stays within the SPEC budget and agrees with the CLI."""

from __future__ import annotations

import re

from paperops.cli import make_parser
from paperops.harness import render_block, skill_source
from paperops.scaffold import scaffold_source

MAX_COMMANDS = 6
MAX_SKILLS = 6


def commands() -> set[str]:
    parser = make_parser()
    actions = [a for a in parser._actions if a.choices and a.dest == "command"]
    return set(actions[0].choices)


def skills() -> list[str]:
    return sorted(p.name for p in skill_source().iterdir() if (p / "SKILL.md").is_file())


def test_budget() -> None:
    assert len(commands()) <= MAX_COMMANDS
    assert len(skills()) <= MAX_SKILLS


def test_block_lists_every_skill_and_only_real_commands() -> None:
    block = render_block("t")
    for name in skills():
        assert f"`{name}`" in block
    assert set(re.findall(r"`(paper-[a-z]+)`", block)) == set(skills())
    assert set(re.findall(r"`pops ([a-z]+)", block)) <= commands()


def test_skills_reference_existing_skills_commands_and_files() -> None:
    scaffold = scaffold_source()
    for name in skills():
        text = (skill_source() / name / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---")[1]
        assert f"name: {name}\n" in front and "description: " in front
        assert set(re.findall(r"`(paper-[a-z]+)`", text)) <= set(skills()), name
        assert set(re.findall(r"`pops ([a-z]+)", text)) <= commands(), name
        for path in re.findall(r"`(figures/[\w./]+)`", text):
            if "<name>" not in path:
                assert (scaffold / path).exists(), f"{name}: {path}"


def test_scaffold_keeps_the_formats_the_cli_reads() -> None:
    scaffold = scaffold_source()
    brief = (scaffold / "BRIEF.md").read_text(encoding="utf-8")
    assert "\n状態: draft\n" in brief
    assert "\n## 主張" in brief and "\n## 未決" in brief
    style = (scaffold / "STYLE.md").read_text(encoding="utf-8")
    assert "\n## 候補" in style and "\n## 共有待ち" in style
    figure = (scaffold / "figures/_template/figure.md").read_text(encoding="utf-8")
    assert "\n状態: draft\n" in figure and "\n## メッセージ" in figure and "\n## 推敲記録" in figure
    # The design sections that paper-figure fills in before any drawing.
    assert "\n## 描く量と形" in figure and "\n## 載せないもの" in figure
