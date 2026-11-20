"""Read BRIEF, STYLE, and figure review notes for the project summary."""

from __future__ import annotations

import re
from pathlib import Path

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_STATUS_RE = re.compile(r"^(?:状態|status)\s*[:：]\s*(\S+)", re.MULTILINE)
_ROUND_RE = re.compile(r"^- R\d+", re.MULTILINE)
_FINDING_RE = re.compile(r"^###\s+(\S+)")
_FINDING_STATUS_RE = re.compile(r"^-\s*(?:状態|status)\s*[:：]\s*([^\s（(]+)")
_CHECKBOX_RE = re.compile(r"^\[([ xX])\](?:\s+|$)")


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


def _open_items(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        if not line.startswith("- "):
            continue
        item = line[2:].strip()
        checkbox = _CHECKBOX_RE.match(item)
        if checkbox:
            if checkbox[1].lower() == "x":
                continue
            item = item[checkbox.end() :]
        if item:
            items.append(item)
    return items


def _findings(lines: list[str]) -> list[dict]:
    """Findings (``### C1 ...``) with their ``- 状態:`` (e.g. 確認済み or 予想)."""
    found: list[dict] = []
    for line in lines:
        heading = _FINDING_RE.match(line)
        status = _FINDING_STATUS_RE.match(line)
        if heading:
            found.append({"id": heading.group(1), "status": ""})
        elif status and found and not found[-1]["status"]:
            found[-1]["status"] = status.group(1)
    return found


def brief_state(root: Path) -> dict:
    path = root / "BRIEF.md"
    text = _read(path)
    sections = _sections(text)
    status = _STATUS_RE.search(text)
    message = ""
    open_items: list[str] = []
    findings: list[dict] = []
    for heading, lines in sections.items():
        if heading.startswith("主張") and not message:
            message = next((ln.strip() for ln in lines if ln.strip()), "")
        elif heading.startswith("未決"):
            open_items.extend(_open_items(lines))
        elif heading.startswith("主要な発見"):
            findings = _findings(lines)
    return {
        "exists": path.is_file(),
        "status": status.group(1) if status else "draft",
        "message": message,
        "findings": findings,
        "open_items": len(open_items),
        "open_item_texts": open_items,
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
