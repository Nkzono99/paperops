"""Collect the project state for ``pops context``."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from paperops import __version__
from paperops.harness import deployed_version
from paperops.project import Project
from paperops.tex import find_comments, outline, read_lines

from ._notes import brief_state, figure_states, style_state
from ._render import render
from ._sources import source_state

__all__ = [
    "PREDICTION_MARK",
    "brief_state",
    "build_state",
    "figure_states",
    "gather",
    "prediction_marks",
    "render",
    "source_state",
    "style_state",
]

PREDICTION_MARK = "\\pred{"


def prediction_marks(tex_files: list[Path], root: Path) -> dict:
    """Where ``\\pred{`` marks remain: results written ahead of the runs that will confirm them."""
    files = {}
    for path in tex_files:
        count = sum(line.text.count(PREDICTION_MARK) for line in read_lines(path))
        if count:
            files[str(path.relative_to(root))] = count
    return {"marks": sum(files.values()), "files": files}


def build_state(project: Project, tex_files: list[Path]) -> dict:
    pdf = project.root / "build" / f"{project.main.stem}.pdf"
    if not pdf.is_file():
        return {"pdf": "", "built": "", "stale": False}
    inputs = [*tex_files, *project.manuscript_dir.glob("*.bib")]
    inputs += list((project.root / "figures").glob("*/*.pdf"))
    built = pdf.stat().st_mtime
    return {
        "pdf": str(pdf.relative_to(project.root)),
        "built": time.strftime("%Y-%m-%d %H:%M", time.localtime(built)),
        "stale": any(p.stat().st_mtime > built for p in inputs if p.is_file()),
    }


def gather(project: Project) -> dict:
    root = project.root
    tex_files = sorted(project.manuscript_dir.rglob("*.tex"))
    paragraphs = []
    if project.main_path.is_file():
        paragraphs = [item for item in outline(project.main_path, root) if item.kind == "paragraph"]
    comments = [asdict(c) for c in find_comments(tex_files, root)]
    brief = brief_state(root)
    deployed = deployed_version(root)

    hints = []
    if deployed and deployed != __version__:
        hints.append(
            f"harness is from paperops {deployed}, installed is {__version__}: pops update"
        )
    if not brief["message"]:
        hints.append("BRIEF.md has no message yet: start with the paper-brief skill")
    elif brief["status"] != "approved":
        hints.append("BRIEF.md is a draft: get the author's approval, or their word to go ahead")
    if comments:
        hints.append(f"{len(comments)} open review comments: paper-revise skill")
    build = build_state(project, tex_files)
    if build["stale"]:
        hints.append("the PDF is older than the manuscript or figures: pops build")

    return {
        "paperops": __version__,
        "title": project.title,
        "lang": project.lang,
        "brief": brief,
        "style": {
            "project": style_state(root / "STYLE.md"),
            "shared": style_state(project.shared_style),
        },
        "sources": [source_state(s) for s in project.sources],
        "manuscript": {
            "main": str(project.main),
            "files": len(tex_files),
            "paragraphs": len(paragraphs),
        },
        "build": build,
        "figures": figure_states(root),
        "predictions": prediction_marks(tex_files, root),
        "comments": comments,
        "next": hints,
    }
