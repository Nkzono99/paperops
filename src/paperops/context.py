"""``pops context``: where the paper stands, read from the project files."""

from __future__ import annotations

import re
import time
from dataclasses import asdict
from pathlib import Path

from paperops import __version__
from paperops.harness import deployed_version
from paperops.project import Project, Source
from paperops.tex import find_comments, outline

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_STATUS_RE = re.compile(r"^(?:状態|status)\s*[:：]\s*(\S+)", re.MULTILINE)
_ROUND_RE = re.compile(r"^- R\d+", re.MULTILINE)
_MAX_TOPICS = 40
_RUN_TREE_DEPTH = 5


def _read(path: Path) -> str:
    try:
        return _HTML_COMMENT_RE.sub("", path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _sections(text: str) -> dict[str, list[str]]:
    """Lines of a markdown file grouped by ``## `` heading."""
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)
    return sections


def _bullets(lines: list[str]) -> int:
    return sum(1 for line in lines if line.startswith("- ") and line[2:].strip())


def _day(path: Path) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime))


def brief_state(root: Path) -> dict:
    path = root / "BRIEF.md"
    text = _read(path)
    sections = _sections(text)
    status = _STATUS_RE.search(text)
    message = ""
    open_items = 0
    for heading, lines in sections.items():
        if heading.startswith("主張") and not message:
            message = next((ln.strip() for ln in lines if ln.strip()), "")
        elif heading.startswith("未決"):
            open_items = _bullets(lines)
    return {
        "exists": path.is_file(),
        "status": status.group(1) if status else "draft",
        "message": message,
        "open_items": open_items,
    }


def style_state(path: Path | None) -> dict:
    if path is None:
        return {"path": "", "exists": False, "rules": 0, "candidates": 0, "pending": 0}
    counts = {"rules": 0, "candidates": 0, "pending": 0}
    for heading, lines in _sections(_read(path)).items():
        if heading.startswith("候補"):
            counts["candidates"] += _bullets(lines)
        elif heading.startswith("共有待ち"):
            counts["pending"] += _bullets(lines)
        else:
            counts["rules"] += _bullets(lines)
    return {"path": str(path), "exists": path.is_file(), **counts}


def _analysis_topics(source: Source) -> list[str]:
    """READMEs of analysis topics in a runops project (project-wide and per run group)."""
    root = source.path
    topics = sorted((root / "analysis").glob("*/README.md")) if (root / "analysis").is_dir() else []

    def walk(directory: Path, depth: int) -> None:
        if depth > _RUN_TREE_DEPTH or len(topics) >= _MAX_TOPICS:
            return
        try:
            children = sorted(p for p in directory.iterdir() if p.is_dir())
        except OSError:
            return
        for child in children:
            if child.name == "_analysis":
                topics.extend(sorted(child.glob("*/README.md")))
            elif child.name.startswith(("_", ".")) or (child / "manifest.toml").is_file():
                continue  # archive, scratch and run directories are not searched
            else:
                walk(child, depth + 1)

    if (root / "runs").is_dir():
        walk(root / "runs", 1)
    return [str(p.relative_to(root)) for p in topics[:_MAX_TOPICS]]


def source_state(source: Source) -> dict:
    exists = source.path.is_dir()
    log = source.path / "LOG.md"
    return {
        "name": source.name,
        "path": str(source.path),
        "note": source.note,
        "exists": exists,
        "runops": exists and source.is_runops,
        "log_updated": _day(log) if log.is_file() else "",
        "analysis": _analysis_topics(source) if exists else [],
    }


def figure_states(root: Path) -> list[dict]:
    figures = []
    base = root / "figures"
    if not base.is_dir():
        return figures
    for directory in sorted(p for p in base.iterdir() if p.is_dir()):
        if directory.name.startswith(("_", ".")):
            continue
        script = directory / "make.py"
        notes = directory / "figure.md"
        if not script.is_file() and not notes.is_file():
            continue
        text = _read(notes)
        status = _STATUS_RE.search(text)
        message = ""
        for heading, lines in _sections(text).items():
            if heading.startswith("メッセージ"):
                message = next((ln.strip() for ln in lines if ln.strip()), "")
        outputs = [directory / f"{directory.name}{ext}" for ext in (".pdf", ".png")]
        outputs = [p for p in outputs if p.is_file()]
        if not outputs:
            output = "missing"
        elif script.is_file() and script.stat().st_mtime > min(p.stat().st_mtime for p in outputs):
            output = "stale"
        else:
            output = "ok"
        figures.append(
            {
                "name": directory.name,
                "status": status.group(1) if status else "draft",
                "message": message,
                "rounds": len(_ROUND_RE.findall(text)),
                "output": output,
            }
        )
    return figures


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
        "comments": comments,
        "next": hints,
    }


def render(state: dict) -> str:
    out = [f"paper: {state['title'] or '(untitled)'}  [{state['lang']}]"]
    brief = state["brief"]
    out.append(f"brief: {brief['status']}  message: {brief['message'] or '(not written)'}")
    if brief["open_items"]:
        out.append(f"  open items in BRIEF.md: {brief['open_items']}")

    for key, label in (("project", "STYLE.md"), ("shared", "shared")):
        style = state["style"][key]
        if not style["path"]:
            continue
        name = label if key == "project" else f"shared {style['path']}"
        if not style["exists"]:
            out.append(f"style: {name} (missing)")
            continue
        extra = f", {style['pending']} waiting to be shared" if style["pending"] else ""
        out.append(
            f"style: {name}: {style['rules']} rules, {style['candidates']} candidates{extra}"
        )

    out.append("sources:" if state["sources"] else "sources: (none; add [[sources]] to paper.toml)")
    for src in state["sources"]:
        if not src["exists"]:
            out.append(f"  - {src['name']}: {src['path']} (missing)")
            continue
        kind = "runops project" if src["runops"] else "directory"
        log = f", LOG.md {src['log_updated']}" if src["log_updated"] else ""
        out.append(f"  - {src['name']}: {src['path']} ({kind}{log})")
        out += [f"      {topic}" for topic in src["analysis"]]

    manuscript = state["manuscript"]
    build = state["build"]
    built = "not built"
    if build["pdf"]:
        built = f"{build['pdf']} {build['built']}" + (" (stale)" if build["stale"] else "")
    out.append(f"manuscript: {manuscript['main']}, {manuscript['paragraphs']} paragraphs; {built}")

    out.append("figures:" if state["figures"] else "figures: (none)")
    for fig in state["figures"]:
        out.append(
            f"  - {fig['name']}: {fig['message'] or '(no message in figure.md)'}\n"
            f"      {fig['status']}, {fig['rounds']} review rounds, "
            f"output {fig['output']}"
        )

    comments = state["comments"]
    out.append(f"comments: {len(comments)} open" if comments else "comments: none open")
    for c in comments:
        out.append(f"  - {c['file']}:{c['line']}: {c['text']}")
        if c["target"]:
            out.append(f"      on: {c['target']}")

    out += [f"next: {hint}" for hint in state["next"]]
    return "\n".join(out)
