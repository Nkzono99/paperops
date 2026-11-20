"""Read TeX lines, expand included files, and locate review comments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

COMMENT_MARK = ">"  # a review comment is a TeX comment that starts with "%>"

_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")


@dataclass(frozen=True)
class Line:
    file: Path
    lineno: int
    text: str  # with the TeX comment removed
    comment: str | None  # text after an unescaped %, or None


@dataclass(frozen=True)
class Comment:
    file: str
    line: int
    text: str
    target: str  # the manuscript text the comment is attached to


def split_comment(raw: str) -> tuple[str, str | None]:
    """Split a raw line at the first unescaped ``%``."""
    i = 0
    while True:
        i = raw.find("%", i)
        if i < 0:
            return raw, None
        backslashes = len(raw[:i]) - len(raw[:i].rstrip("\\"))
        if backslashes % 2 == 0:
            return raw[:i], raw[i + 1 :]
        i += 1


def read_lines(path: Path) -> list[Line]:
    lines = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text, comment = split_comment(raw)
        lines.append(Line(path, number, text, comment))
    return lines


def expand(main: Path, _seen: frozenset[Path] = frozenset()) -> list[Line]:
    """Lines of ``main`` with ``\\input`` files inlined (resolved from the main directory)."""
    return _expand(main, main.parent, _seen)


def _expand(path: Path, base: Path, seen: frozenset[Path]) -> list[Line]:
    if path in seen or not path.is_file():
        return []
    out: list[Line] = []
    for line in read_lines(path):
        match = _INPUT_RE.search(line.text)
        if not match:
            out.append(line)
            continue
        target = base / match.group(1).strip()
        if not target.suffix:
            target = target.with_suffix(".tex")
        out.extend(_expand(target, base, seen | {path}))
    return out


def find_comments(files: list[Path], root: Path) -> list[Comment]:
    """Open review comments: ``%>`` lines (consecutive lines merge) and inline ``%>``."""
    found: list[Comment] = []
    for path in files:
        lines = read_lines(path)
        rel = str(path.relative_to(root))
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.comment is None or not line.comment.startswith(COMMENT_MARK):
                i += 1
                continue
            start = i
            parts = [line.comment[1:].strip()]
            if line.text.strip():  # inline comment: attached to its own line
                target = line.text.strip()
                i += 1
            else:
                i += 1
                while (
                    i < len(lines)
                    and not lines[i].text.strip()
                    and (lines[i].comment or "").startswith(COMMENT_MARK)
                ):
                    parts.append((lines[i].comment or "")[1:].strip())
                    i += 1
                target = next((ln.text.strip() for ln in lines[i:] if ln.text.strip()), "")
            found.append(
                Comment(rel, lines[start].lineno, " ".join(p for p in parts if p), _clip(target))
            )
    return found


def _clip(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
